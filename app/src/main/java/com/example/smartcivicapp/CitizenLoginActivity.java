package com.example.smartcivicapp;

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

public class CitizenLoginActivity extends AppCompatActivity {

    private static final String TAG = "CitizenLogin";

    private EditText etEmail, etPassword;
    private Button btnLogin;
    private DatabaseHelper db;
    private PrefManager pref;
    private AuthRepository authRepo;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        RetrofitClient.init(this);
        setContentView(R.layout.activity_citizen_login);

        etEmail    = findViewById(R.id.etEmail);
        etPassword = findViewById(R.id.etPassword);
        btnLogin   = findViewById(R.id.btnLogin);
        TextView tvRegister = findViewById(R.id.tvRegister);

        db       = new DatabaseHelper(this);
        pref     = new PrefManager(this);
        authRepo = new AuthRepository(this);

        btnLogin.setOnClickListener(v -> attemptLogin());
        tvRegister.setOnClickListener(v ->
                startActivity(new Intent(this, CitizenRegisterActivity.class)));
    }

    private void attemptLogin() {
        String email    = etEmail.getText().toString().trim();
        String password = etPassword.getText().toString().trim();

        if (TextUtils.isEmpty(email)) {
            etEmail.setError("Email is required");
            return;
        }
        if (!android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            etEmail.setError("Please enter a valid email address");
            return;
        }
        if (TextUtils.isEmpty(password)) {
            etPassword.setError("Password is required");
            return;
        }

        btnLogin.setEnabled(false);
        btnLogin.setText("Logging in...");

        Log.d(TAG, "Attempting citizen login for: " + email);

        authRepo.login(email, password, new AuthRepository.AuthCallback() {
            @Override
            public void onSuccess(TokenResponse response) {
                btnLogin.setEnabled(true);
                btnLogin.setText("LOGIN");

                Log.d(TAG, String.format("Citizen login SUCCESS -> User: %s | Role: %s | HasToken: %b | IsLoggedIn: %b",
                        response.userId, response.role, !pref.getAuthToken().isEmpty(), pref.isCitizenLoggedIn()));

                Toast.makeText(CitizenLoginActivity.this, "Welcome " + response.name + "!", Toast.LENGTH_SHORT).show();
                navigateToHome();
            }

            @Override
            public void onError(String message, int statusCode) {
                btnLogin.setEnabled(true);
                btnLogin.setText("LOGIN");
                Log.e(TAG, String.format("Citizen login ERROR -> HTTP %d: %s", statusCode, message));
                Toast.makeText(CitizenLoginActivity.this, message, Toast.LENGTH_LONG).show();
            }

            @Override
            public void onFailure(Throwable throwable) {
                btnLogin.setEnabled(true);
                btnLogin.setText("LOGIN");
                Log.e(TAG, "Citizen login NETWORK FAILURE -> " + throwable.getMessage(), throwable);
                Toast.makeText(CitizenLoginActivity.this, "Cannot reach backend: " + throwable.getMessage(), Toast.LENGTH_LONG).show();
            }
        });
    }

    private void navigateToHome() {
        Intent intent = new Intent(this, CitizenHomeActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
        startActivity(intent);
        finish();
    }
}
