package com.example.smartcivicapp.repositories;

import android.content.Context;
import android.util.Log;

import com.example.smartcivicapp.PrefManager;
import com.example.smartcivicapp.network.ReportApiService;
import com.example.smartcivicapp.network.RetrofitClient;
import com.example.smartcivicapp.network.models.AdminStatsResponse;
import com.example.smartcivicapp.network.models.LoginRequest;
import com.example.smartcivicapp.network.models.NotificationListResponse;
import com.example.smartcivicapp.network.models.RegisterRequest;
import com.example.smartcivicapp.network.models.TokenResponse;
import com.example.smartcivicapp.network.models.UserProfileResponse;

import org.json.JSONArray;
import org.json.JSONObject;

import okhttp3.ResponseBody;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class AuthRepository {

    private static final String TAG = "AuthRepository";

    public interface AuthCallback {
        void onSuccess(TokenResponse response);
        void onError(String message, int statusCode);
        void onFailure(Throwable throwable);
    }

    public interface ProfileCallback {
        void onSuccess(UserProfileResponse profile);
        void onError(String message, int statusCode);
        void onFailure(Throwable throwable);
    }

    public interface AdminStatsCallback {
        void onSuccess(AdminStatsResponse stats);
        void onError(String message, int statusCode);
        void onFailure(Throwable throwable);
    }

    public interface NotificationListCallback {
        void onSuccess(NotificationListResponse response);
        void onError(String message, int statusCode);
        void onFailure(Throwable throwable);
    }

    public interface SimpleCallback {
        void onSuccess();
        void onError(String message);
    }

    private final ReportApiService apiService;
    private final PrefManager prefManager;

    public AuthRepository(Context context) {
        if (context != null) {
            RetrofitClient.init(context);
        }
        this.apiService = RetrofitClient.getReportApiService();
        this.prefManager = new PrefManager(context);
    }

    public void login(String email, String password, AuthCallback callback) {
        Log.d(TAG, String.format("[POST] /api/v1/auth/login -> Request started for email=%s", email));

        apiService.login(new LoginRequest(email, password)).enqueue(new Callback<TokenResponse>() {
            @Override
            public void onResponse(Call<TokenResponse> call, Response<TokenResponse> response) {
                int code = response.code();
                if (response.isSuccessful() && response.body() != null) {
                    TokenResponse tokenResponse = response.body();
                    prefManager.saveSession(tokenResponse);

                    boolean tokenStored = !prefManager.getAuthToken().isEmpty();
                    boolean isAdmin = prefManager.isAdmin();
                    boolean isLoggedIn = isAdmin ? prefManager.isAdminLoggedIn() : prefManager.isCitizenLoggedIn();

                    Log.d(TAG, String.format("[POST] /api/v1/auth/login -> SUCCESS HTTP %d | User: %s | Role: %s | TokenSaved: %b | IsLoggedIn: %b",
                            code, tokenResponse.userId, tokenResponse.role, tokenStored, isLoggedIn));

                    callback.onSuccess(tokenResponse);
                } else {
                    String errorDetail = extractErrorDetail(response);
                    Log.e(TAG, String.format("[POST] /api/v1/auth/login -> FAILED HTTP %d | %s", code, errorDetail));
                    callback.onError(errorDetail, code);
                }
            }

            @Override
            public void onFailure(Call<TokenResponse> call, Throwable t) {
                Log.e(TAG, "[POST] /api/v1/auth/login -> NETWORK FAILURE: " + t.getMessage(), t);
                callback.onFailure(t);
            }
        });
    }

    public void register(String name, String email, String phone, String password, AuthCallback callback) {
        Log.d(TAG, String.format("[POST] /api/v1/auth/register -> Request started for email=%s, name=%s", email, name));

        apiService.register(new RegisterRequest(name, email, phone, password)).enqueue(new Callback<TokenResponse>() {
            @Override
            public void onResponse(Call<TokenResponse> call, Response<TokenResponse> response) {
                int code = response.code();
                if (response.isSuccessful() && response.body() != null) {
                    TokenResponse tokenResponse = response.body();
                    prefManager.saveSession(tokenResponse);

                    boolean tokenStored = !prefManager.getAuthToken().isEmpty();
                    boolean isLoggedIn = prefManager.isCitizenLoggedIn();

                    Log.d(TAG, String.format("[POST] /api/v1/auth/register -> SUCCESS HTTP %d | User: %s | Role: %s | TokenSaved: %b | IsLoggedIn: %b",
                            code, tokenResponse.userId, tokenResponse.role, tokenStored, isLoggedIn));

                    callback.onSuccess(tokenResponse);
                } else {
                    String errorDetail = extractErrorDetail(response);
                    Log.e(TAG, String.format("[POST] /api/v1/auth/register -> FAILED HTTP %d | %s", code, errorDetail));
                    callback.onError(errorDetail, code);
                }
            }

            @Override
            public void onFailure(Call<TokenResponse> call, Throwable t) {
                Log.e(TAG, "[POST] /api/v1/auth/register -> NETWORK FAILURE: " + t.getMessage(), t);
                callback.onFailure(t);
            }
        });
    }

    public void getProfile(ProfileCallback callback) {
        apiService.getProfile().enqueue(new Callback<UserProfileResponse>() {
            @Override
            public void onResponse(Call<UserProfileResponse> call, Response<UserProfileResponse> response) {
                if (response.isSuccessful() && response.body() != null) {
                    callback.onSuccess(response.body());
                } else {
                    callback.onError(extractErrorDetail(response), response.code());
                }
            }

            @Override
            public void onFailure(Call<UserProfileResponse> call, Throwable t) {
                callback.onFailure(t);
            }
        });
    }

    public void getAdminStats(AdminStatsCallback callback) {
        apiService.getAdminStats().enqueue(new Callback<AdminStatsResponse>() {
            @Override
            public void onResponse(Call<AdminStatsResponse> call, Response<AdminStatsResponse> response) {
                if (response.isSuccessful() && response.body() != null) {
                    callback.onSuccess(response.body());
                } else {
                    callback.onError(extractErrorDetail(response), response.code());
                }
            }

            @Override
            public void onFailure(Call<AdminStatsResponse> call, Throwable t) {
                callback.onFailure(t);
            }
        });
    }

    public void getNotifications(NotificationListCallback callback) {
        apiService.getNotifications().enqueue(new Callback<NotificationListResponse>() {
            @Override
            public void onResponse(Call<NotificationListResponse> call, Response<NotificationListResponse> response) {
                if (response.isSuccessful() && response.body() != null) {
                    callback.onSuccess(response.body());
                } else {
                    callback.onError(extractErrorDetail(response), response.code());
                }
            }

            @Override
            public void onFailure(Call<NotificationListResponse> call, Throwable t) {
                callback.onFailure(t);
            }
        });
    }

    public void markNotificationRead(String notificationId, SimpleCallback callback) {
        apiService.markNotificationRead(notificationId).enqueue(new Callback<ResponseBody>() {
            @Override
            public void onResponse(Call<ResponseBody> call, Response<ResponseBody> response) {
                if (response.isSuccessful()) {
                    callback.onSuccess();
                } else {
                    callback.onError(extractErrorDetail(response));
                }
            }

            @Override
            public void onFailure(Call<ResponseBody> call, Throwable t) {
                callback.onError(t.getMessage());
            }
        });
    }

    /**
     * Extracts a sanitized, human-readable error description from an HTTP error response.
     */
    private String extractErrorDetail(Response<?> response) {
        int code = response.code();
        String rawBody = "";
        try {
            if (response.errorBody() != null) {
                rawBody = response.errorBody().string();
            }
        } catch (Exception ignored) {}

        if (rawBody == null || rawBody.trim().isEmpty()) {
            if (code == 401) return "401: Invalid email or password";
            if (code == 403) return "403: Access forbidden";
            if (code == 404) return "404: Not found";
            if (code == 409) return "409: Email is already registered";
            if (code == 422) return "422: Invalid input data format";
            return "HTTP " + code + ": Request failed";
        }

        try {
            JSONObject obj = new JSONObject(rawBody);
            if (obj.has("detail")) {
                Object detailObj = obj.get("detail");
                if (detailObj instanceof String) {
                    return code + ": " + detailObj;
                } else if (detailObj instanceof JSONArray) {
                    JSONArray arr = (JSONArray) detailObj;
                    StringBuilder sb = new StringBuilder();
                    for (int i = 0; i < arr.length(); i++) {
                        JSONObject item = arr.getJSONObject(i);
                        if (item.has("msg")) {
                            if (sb.length() > 0) sb.append(", ");
                            sb.append(item.getString("msg"));
                        }
                    }
                    if (sb.length() > 0) {
                        return code + ": " + sb.toString();
                    }
                }
            }
        } catch (Exception ignored) {}

        return code + ": " + rawBody.trim();
    }
}
