package com.example.smartcivicapp;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import android.util.Log;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.example.smartcivicapp.database.DatabaseHelper;
import com.example.smartcivicapp.network.RetrofitClient;
import com.example.smartcivicapp.network.models.TokenResponse;
import com.example.smartcivicapp.repositories.AuthRepository;
import com.example.smartcivicapp.utils.LocaleHelper;

public class CitizenRegisterActivity extends AppCompatActivity {

    private static final String TAG = "CitizenRegister";

    private EditText etName, etEmail, etPhone, etPassword;
    private Button btnRegister;
    private DatabaseHelper db;
    private AuthRepository authRepo;

    @Override
    protected void attachBaseContext(Context newBase) {
        super.attachBaseContext(LocaleHelper.onAttach(newBase));
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        RetrofitClient.init(this);
        setContentView(R.layout.activity_citizen_register);

        etName      = findViewById(R.id.etName);
        etEmail     = findViewById(R.id.etEmail);
        etPhone     = findViewById(R.id.etPhone);
        etPassword  = findViewById(R.id.etPassword);
        btnRegister = findViewById(R.id.btnRegister);
        TextView tvLoginLink = findViewById(R.id.tvLoginLink);

        db       = new DatabaseHelper(this);
        authRepo = new AuthRepository(this);
        btnRegister.setOnClickListener(v -> attemptRegister());
        if (tvLoginLink != null) {
            tvLoginLink.setOnClickListener(v -> finish());
        }
    }

    private void attemptRegister() {
        String name     = etName.getText().toString().trim();
        String email    = etEmail.getText().toString().trim();
        String phone    = etPhone.getText().toString().trim();
        String password = etPassword.getText().toString().trim();

        if (TextUtils.isEmpty(name)) {
            etName.setError(getString(R.string.err_name_required));
            return;
        }
        if (TextUtils.isEmpty(email)) {
            etEmail.setError(getString(R.string.err_email_required));
            return;
        }
        if (!android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            etEmail.setError(getString(R.string.err_email_invalid));
            return;
        }
        if (password.length() < 6) {
            etPassword.setError(getString(R.string.err_password_min));
            return;
        }

        btnRegister.setEnabled(false);
        btnRegister.setText(R.string.msg_registering);

        // Save locally in SQLite for offline resilience
        db.registerCitizen(name, email, phone, password);

        Log.d(TAG, String.format("Attempting registration: Name=%s, Email=%s, Phone=%s", name, email, phone));

        authRepo.register(name, email, phone, password, new AuthRepository.AuthCallback() {
            @Override
            public void onSuccess(TokenResponse response) {
                btnRegister.setEnabled(true);
                btnRegister.setText(R.string.btn_register);
                PrefManager pref = new PrefManager(CitizenRegisterActivity.this);
                Log.d(TAG, String.format("Registration SUCCESS -> User: %s | Role: %s | HasToken: %b | IsLoggedIn: %b",
                        response.userId, response.role, !pref.getAuthToken().isEmpty(), pref.isCitizenLoggedIn()));

                Toast.makeText(CitizenRegisterActivity.this, getString(R.string.msg_welcome, response.name), Toast.LENGTH_SHORT).show();
                Intent intent = new Intent(CitizenRegisterActivity.this, CitizenHomeActivity.class);
                intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
                startActivity(intent);
                finish();
            }

            @Override
            public void onError(String message, int statusCode) {
                btnRegister.setEnabled(true);
                btnRegister.setText(R.string.btn_register);
                Log.e(TAG, String.format("Registration ERROR -> HTTP %d: %s", statusCode, message));
                Toast.makeText(CitizenRegisterActivity.this, message, Toast.LENGTH_LONG).show();
            }

            @Override
            public void onFailure(Throwable throwable) {
                btnRegister.setEnabled(true);
                btnRegister.setText(R.string.btn_register);
                Log.e(TAG, "Registration NETWORK FAILURE -> " + throwable.getMessage(), throwable);
                Toast.makeText(CitizenRegisterActivity.this, "Cannot reach backend: " + throwable.getMessage(), Toast.LENGTH_LONG).show();
            }
        });
    }
}
