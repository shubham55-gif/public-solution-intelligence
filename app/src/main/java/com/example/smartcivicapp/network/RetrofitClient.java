package com.example.smartcivicapp.network;

import android.content.Context;
import android.text.TextUtils;
import android.util.Log;

import com.example.smartcivicapp.BuildConfig;
import com.example.smartcivicapp.PrefManager;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

import okhttp3.Interceptor;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

/** Provides one Retrofit instance configured from the Gradle backend URL property. */
public final class RetrofitClient {

    private static final String TAG = "RetrofitClient";
    private static volatile ReportApiService reportApiService;
    private static Context appContext;

    private RetrofitClient() {}

    public static void init(Context context) {
        if (context != null) {
            appContext = context.getApplicationContext();
        }
    }

    public static ReportApiService getReportApiService() {
        if (reportApiService == null) {
            synchronized (RetrofitClient.class) {
                if (reportApiService == null) {
                    HttpLoggingInterceptor logging = new HttpLoggingInterceptor();
                    logging.setLevel(BuildConfig.DEBUG
                            ? HttpLoggingInterceptor.Level.HEADERS
                            : HttpLoggingInterceptor.Level.NONE);

                    Interceptor authInterceptor = new Interceptor() {
                        @Override
                        public Response intercept(Chain chain) throws IOException {
                            Request original = chain.request();
                            Request.Builder builder = original.newBuilder();

                            String token = "";
                            String userId = "";
                            String role = "ANONYMOUS";

                            if (appContext != null) {
                                PrefManager pref = new PrefManager(appContext);
                                token = pref.getAuthToken();
                                userId = pref.getUserId();
                                role = pref.getUserRole();
                            }

                            if (!TextUtils.isEmpty(token)) {
                                builder.header("Authorization", "Bearer " + token);
                                builder.removeHeader("X-Development-User-Id");
                            } else if (!TextUtils.isEmpty(userId)) {
                                builder.header("X-Development-User-Id", userId);
                            } else if (!TextUtils.isEmpty(BuildConfig.BACKEND_DEVELOPMENT_USER_ID)) {
                                builder.header("X-Development-User-Id", BuildConfig.BACKEND_DEVELOPMENT_USER_ID);
                            }

                            Request request = builder.build();
                            Response response = chain.proceed(request);

                            // Safe logging: method, path, HTTP status, user UUID, role (never full JWT)
                            Log.d(TAG, String.format("[%s] %s -> HTTP %d | User: %s | Role: %s",
                                    request.method(),
                                    request.url().encodedPath(),
                                    response.code(),
                                    !TextUtils.isEmpty(userId) ? userId : "N/A",
                                    !TextUtils.isEmpty(role) ? role : "N/A"));

                            return response;
                        }
                    };

                    OkHttpClient client = new OkHttpClient.Builder()
                            .connectTimeout(30, TimeUnit.SECONDS)
                            .readTimeout(60, TimeUnit.SECONDS)
                            .writeTimeout(60, TimeUnit.SECONDS)
                            .addInterceptor(authInterceptor)
                            .addInterceptor(logging)
                            .build();

                    Retrofit retrofit = new Retrofit.Builder()
                            .baseUrl(BuildConfig.BACKEND_BASE_URL)
                            .client(client)
                            .addConverterFactory(GsonConverterFactory.create())
                            .build();

                    reportApiService = retrofit.create(ReportApiService.class);
                }
            }
        }
        return reportApiService;
    }
}
