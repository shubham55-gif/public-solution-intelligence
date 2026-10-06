package com.example.smartcivicapp;

import android.content.Context;
import android.content.SharedPreferences;
import android.text.TextUtils;
import android.util.Log;

import com.example.smartcivicapp.network.models.TokenResponse;

/**
 * PrefManager — session and authentication management via SharedPreferences.
 */
public class PrefManager {

    private static final String TAG                   = "PrefManager";
    private static final String PREF_NAME             = "SMART_CIVIC_PREF";
    private static final String KEY_ROLE              = "USER_ROLE";
    private static final String KEY_ADMIN_LOGGED_IN   = "ADMIN_LOGGED_IN";
    private static final String KEY_CITIZEN_LOGGED_IN = "CITIZEN_LOGGED_IN";
    private static final String KEY_CITIZEN_EMAIL     = "CITIZEN_EMAIL";
    private static final String KEY_CITIZEN_NAME      = "CITIZEN_NAME";
    private static final String KEY_USER_ID           = "USER_ID";
    private static final String KEY_AUTH_TOKEN        = "AUTH_TOKEN";
    private static final String KEY_USER_PHONE        = "USER_PHONE";

    private final SharedPreferences pref;

    public PrefManager(Context context) {
        pref = context.getApplicationContext().getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
    }

    public void saveSession(TokenResponse tokenResponse) {
        if (tokenResponse == null) return;
        boolean isAdmin = "authority".equalsIgnoreCase(tokenResponse.role) || "admin".equalsIgnoreCase(tokenResponse.role);
        String roleStr = isAdmin ? "ADMIN" : "CITIZEN";

        pref.edit()
            .putString(KEY_AUTH_TOKEN, tokenResponse.accessToken != null ? tokenResponse.accessToken : "")
            .putString(KEY_USER_ID, tokenResponse.userId != null ? tokenResponse.userId : "")
            .putString(KEY_CITIZEN_NAME, tokenResponse.name != null ? tokenResponse.name : "")
            .putString(KEY_CITIZEN_EMAIL, tokenResponse.email != null ? tokenResponse.email : "")
            .putString(KEY_USER_PHONE, tokenResponse.phone != null ? tokenResponse.phone : "")
            .putString(KEY_ROLE, roleStr)
            .putBoolean(KEY_ADMIN_LOGGED_IN, isAdmin)
            .putBoolean(KEY_CITIZEN_LOGGED_IN, !isAdmin)
            .commit();

        Log.d(TAG, String.format("Session saved synchronously: User=%s | Role=%s | HasToken=%b | IsAdminLoggedIn=%b | IsCitizenLoggedIn=%b",
                getUserId(), getUserRole(), !getAuthToken().isEmpty(), isAdminLoggedIn(), isCitizenLoggedIn()));
    }

    public void loginAdmin(String username) {
        pref.edit()
            .putString(KEY_ROLE, "ADMIN")
            .putBoolean(KEY_ADMIN_LOGGED_IN, true)
            .commit();
    }

    public void loginCitizen(String email, String name) {
        pref.edit()
            .putString(KEY_ROLE, "CITIZEN")
            .putBoolean(KEY_CITIZEN_LOGGED_IN, true)
            .putString(KEY_CITIZEN_EMAIL, email)
            .putString(KEY_CITIZEN_NAME, name)
            .commit();
    }

    public String getAuthToken() {
        return pref.getString(KEY_AUTH_TOKEN, "");
    }

    public String getUserId() {
        return pref.getString(KEY_USER_ID, "");
    }

    public String getUserPhone() {
        return pref.getString(KEY_USER_PHONE, "");
    }

    public String getUserRole() {
        return pref.getString(KEY_ROLE, "");
    }

    public boolean isAdmin() {
        String role = getUserRole();
        return "ADMIN".equalsIgnoreCase(role) || "AUTHORITY".equalsIgnoreCase(role);
    }

    public boolean isCitizen() {
        String role = getUserRole();
        return "CITIZEN".equalsIgnoreCase(role);
    }

    public boolean isAdminLoggedIn() {
        return pref.getBoolean(KEY_ADMIN_LOGGED_IN, false) && isAdmin() && !TextUtils.isEmpty(getAuthToken());
    }

    public boolean isCitizenLoggedIn() {
        return pref.getBoolean(KEY_CITIZEN_LOGGED_IN, false) && isCitizen() && !TextUtils.isEmpty(getAuthToken());
    }

    public String getCitizenEmail() {
        return pref.getString(KEY_CITIZEN_EMAIL, "");
    }

    public String getCitizenName() {
        return pref.getString(KEY_CITIZEN_NAME, "Citizen");
    }

    public void logout() {
        Log.d(TAG, "Logging out user: " + getUserId());
        pref.edit().clear().commit();
    }
}
