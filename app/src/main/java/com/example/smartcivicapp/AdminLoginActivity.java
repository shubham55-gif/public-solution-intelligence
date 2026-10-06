package com.example.smartcivicapp;

import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import android.util.Log;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.example.smartcivicapp.database.DatabaseHelper;
import com.example.smartcivicapp.network.RetrofitClient;
import com.example.smartcivicapp.network.models.TokenResponse;
import com.example.smartcivicapp.repositories.AuthRepository;

public class AdminLoginActivity extends AppCompatActivity {

    private static final String TAG = "AdminLogin";

    private EditText etUsername, etPassword;
    private Button btnLogin;
    private DatabaseHelper db;
    private PrefManager pref;
    private AuthRepository authRepo;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        RetrofitClient.init(this);
        setContentView(R.layout.admin_login_activity);

        etUsername = findViewById(R.id.etUsername);
        etPassword = findViewById(R.id.etPassword);
        btnLogin   = findViewById(R.id.btnLogin);

        db       = new DatabaseHelper(this);
        pref     = new PrefManager(this);
        authRepo = new AuthRepository(this);

        btnLogin.setOnClickListener(v -> attemptAdminLogin());
    }

    private void attemptAdminLogin() {
        String username = etUsername.getText().toString().trim();
        String password = etPassword.getText().toString().trim();

        if (TextUtils.isEmpty(username)) {
            etUsername.setError("Email/Username is required");
            return;
        }
        if (TextUtils.isEmpty(password)) {
            etPassword.setError("Password is required");
            return;
        }

        btnLogin.setEnabled(false);
        btnLogin.setText("Authenticating...");

        // Map plain 'admin' username to admin email if not an email format
        String email = username.contains("@") ? username : (username.equalsIgnoreCase("admin") ? "admin@example.com" : username + "@example.com");

        Log.d(TAG, "Attempting admin authentication for: " + email);

        authRepo.login(email, password, new AuthRepository.AuthCallback() {
            @Override
            public void onSuccess(TokenResponse response) {
                btnLogin.setEnabled(true);
                btnLogin.setText("LOGIN");

                boolean isAdmin = "authority".equalsIgnoreCase(response.role) || "admin".equalsIgnoreCase(response.role);
                Log.d(TAG, String.format("Admin login SUCCESS -> User: %s | Role: %s | IsAdmin: %b | HasToken: %b",
                        response.userId, response.role, isAdmin, !pref.getAuthToken().isEmpty()));

                if (isAdmin) {
                    Toast.makeText(AdminLoginActivity.this, "Authority access granted", Toast.LENGTH_SHORT).show();
                    Intent intent = new Intent(AdminLoginActivity.this, AdminHomeActivity.class);
                    intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
                    startActivity(intent);
                    finish();
                } else {
                    Log.w(TAG, "User role is not authority/admin: " + response.role);
                    Toast.makeText(AdminLoginActivity.this, "Access denied: Authority role required (Your role: " + response.role + ")", Toast.LENGTH_LONG).show();
                    pref.logout();
                }
            }

            @Override
            public void onError(String message, int statusCode) {
                btnLogin.setEnabled(true);
                btnLogin.setText("LOGIN");
                Log.e(TAG, String.format("Admin login ERROR -> HTTP %d: %s", statusCode, message));
                Toast.makeText(AdminLoginActivity.this, message, Toast.LENGTH_LONG).show();
                etPassword.setText("");
            }

            @Override
            public void onFailure(Throwable throwable) {
                btnLogin.setEnabled(true);
                btnLogin.setText("LOGIN");
                Log.e(TAG, "Admin login NETWORK FAILURE -> " + throwable.getMessage(), throwable);
                Toast.makeText(AdminLoginActivity.this, "Cannot reach backend: " + throwable.getMessage(), Toast.LENGTH_LONG).show();
            }
        });
    }
}
