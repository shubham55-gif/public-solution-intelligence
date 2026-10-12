package com.example.smartcivicapp;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Spinner;

import androidx.appcompat.app.AppCompatActivity;

import com.example.smartcivicapp.utils.LocaleHelper;

/**
 * RoleSelectionActivity — landing page after splash.
 * Checks for existing sessions to skip login if already authenticated.
 * Provides entry-point language selection (English, Marathi, Hindi) for Citizen flow.
 */
public class RoleSelectionActivity extends AppCompatActivity {

    private static final String[] LANGUAGE_NAMES = {"English", "मराठी", "हिंदी"};
    private Spinner spinnerLanguage;
    private PrefManager pref;

    @Override
    protected void attachBaseContext(Context newBase) {
        super.attachBaseContext(LocaleHelper.onAttach(newBase));
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Check for existing session before showing UI
        pref = new PrefManager(this);
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
        spinnerLanguage = findViewById(R.id.spinnerRoleLanguage);

        if (spinnerLanguage != null) {
            ArrayAdapter<String> adapter = new ArrayAdapter<>(
                    this,
                    android.R.layout.simple_spinner_item,
                    LANGUAGE_NAMES
            );
            adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
            spinnerLanguage.setAdapter(adapter);

            String currentLang = pref.getLanguage();
            int selectedIndex = 0;
            if (LocaleHelper.LANGUAGE_MARATHI.equalsIgnoreCase(currentLang)) {
                selectedIndex = 1;
            } else if (LocaleHelper.LANGUAGE_HINDI.equalsIgnoreCase(currentLang)) {
                selectedIndex = 2;
            }
            spinnerLanguage.setSelection(selectedIndex);

            spinnerLanguage.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
                @Override
                public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                    saveLanguageSelection(position);
                }

                @Override
                public void onNothingSelected(AdapterView<?> parent) {}
            });
        }

        if (btnCitizen != null) {
            btnCitizen.setOnClickListener(v -> {
                if (spinnerLanguage != null) {
                    saveLanguageSelection(spinnerLanguage.getSelectedItemPosition());
                }
                startActivity(new Intent(this, CitizenLoginActivity.class));
            });
        }

        if (btnAdmin != null) {
            btnAdmin.setOnClickListener(v -> {
                LocaleHelper.setLocale(this, LocaleHelper.LANGUAGE_ENGLISH);
                startActivity(new Intent(this, AdminLoginActivity.class));
            });
        }
    }

    private void saveLanguageSelection(int position) {
        String lang = LocaleHelper.LANGUAGE_ENGLISH;
        if (position == 1) {
            lang = LocaleHelper.LANGUAGE_MARATHI;
        } else if (position == 2) {
            lang = LocaleHelper.LANGUAGE_HINDI;
        }
        pref.setLanguage(lang);
    }
}
