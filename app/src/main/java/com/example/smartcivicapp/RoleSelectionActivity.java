package com.example.smartcivicapp;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;

import androidx.appcompat.app.AppCompatActivity;

/**
 * RoleSelectionActivity — landing page after splash.
 * Checks for existing sessions to skip login if already authenticated.
 */
public class RoleSelectionActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Check for existing session before showing UI
        PrefManager pref = new PrefManager(this);
        if (pref.isAdminLoggedIn()) {
            startActivity(new Intent(this, AdminHomeActivity.class));
            finish();
            return;
        } else if (pref.isCitizenLoggedIn()) {
            startActivity(new Intent(this, CitizenHomeActivity.class));
            finish();
            return;
        }

        setContentView(R.layout.activity_role_selection);

        View btnCitizen = findViewById(R.id.btnCitizen);
        View btnAdmin   = findViewById(R.id.btnAdmin);

        if (btnCitizen != null) {
            btnCitizen.setOnClickListener(v ->
                    startActivity(new Intent(this, CitizenLoginActivity.class)));
        }

        if (btnAdmin != null) {
            btnAdmin.setOnClickListener(v ->
                    startActivity(new Intent(this, AdminLoginActivity.class)));
        }
    }
}
