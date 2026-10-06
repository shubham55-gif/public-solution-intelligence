package com.example.smartcivicapp.repositories;

import android.text.TextUtils;
import android.util.Log;

import com.example.smartcivicapp.BuildConfig;
import com.example.smartcivicapp.entities.Complaint;
import com.example.smartcivicapp.network.ReportApiService;
import com.example.smartcivicapp.network.RetrofitClient;
import com.example.smartcivicapp.network.models.AIIntelligenceResponse;
import com.example.smartcivicapp.network.models.AdminReportListResponse;
import com.example.smartcivicapp.network.models.RemoteReportPage;
import com.example.smartcivicapp.network.models.RemoteReportResponse;
import com.example.smartcivicapp.network.models.ReportStatusUpdate;
import com.example.smartcivicapp.network.models.ReportSubmission;
import com.example.smartcivicapp.network.models.RemoteReportMapper;

import java.io.File;
import java.net.URLConnection;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/** Coordinates report network operations and mapping to Room database models. */
public class ReportRepository {

    private static final String TAG = "ReportRepository";
    private static final MediaType TEXT_PLAIN = MediaType.parse("text/plain");
    private static final MediaType JPEG = MediaType.parse("image/jpeg");

    public interface SubmitCallback {
        void onSuccess(RemoteReportResponse response);
        void onHttpError(int statusCode);
        void onConnectionFailure(Throwable throwable);
        void onConfigurationError(String message);
    }

    public interface ReportListCallback {
        void onSuccess(List<Complaint> reports);
        void onHttpError(int statusCode);
        void onMalformedResponse(Throwable throwable);
        void onFailure(Throwable throwable);
        void onConfigurationError(String message);
    }

    public interface AdminReportListCallback {
        void onSuccess(List<RemoteReportResponse> reports, int total);
        void onHttpError(int statusCode);
        void onFailure(Throwable throwable);
        void onConfigurationError(String message);
    }

    public interface StatusUpdateCallback {
        void onSuccess(RemoteReportResponse response);
        void onHttpError(int statusCode);
        void onConnectionFailure(Throwable throwable);
        void onConfigurationError(String message);
    }

    public interface AIIntelligenceCallback {
        void onSuccess(AIIntelligenceResponse response);
        void onHttpError(int statusCode);
        void onFailure(Throwable throwable);
        void onConfigurationError(String message);
    }

    private final ReportApiService apiService;
    private android.content.Context context;

    public ReportRepository() {
        this(RetrofitClient.getReportApiService());
    }

    public ReportRepository(android.content.Context context) {
        this(RetrofitClient.getReportApiService());
        this.context = context != null ? context.getApplicationContext() : null;
    }

    ReportRepository(ReportApiService apiService) {
        this.apiService = apiService;
    }

    public void submitReport(ReportSubmission submission, SubmitCallback callback) {
        MultipartBody.Part imagePart = buildImagePart(submission.getImageFile());
        Call<RemoteReportResponse> call = apiService.createReport(
                textPart(submission.getIssueCategory()),
                textPart(submission.getDescription()),
                textPart(String.format(Locale.US, "%.6f", submission.getLatitude())),
                textPart(String.format(Locale.US, "%.6f", submission.getLongitude())),
                textPart(submission.getReportedAt()),
                textPart(submission.getSeverity()),
                imagePart
        );

        call.enqueue(new Callback<RemoteReportResponse>() {
            @Override
            public void onResponse(Call<RemoteReportResponse> call,
                                   Response<RemoteReportResponse> response) {
                if (response.isSuccessful() && response.body() != null) {
                    Log.d(TAG, "Remote report submission completed");
                    callback.onSuccess(response.body());
                } else {
                    Log.w(TAG, "Remote report submission returned HTTP " + response.code());
                    callback.onHttpError(response.code());
                }
            }

            @Override
            public void onFailure(Call<RemoteReportResponse> call, Throwable throwable) {
                Log.w(TAG, "Remote report submission failed: "
                        + throwable.getClass().getSimpleName());
                callback.onConnectionFailure(throwable);
            }
        });
    }

    public void getMyReports(ReportListCallback callback) {
        apiService.getMyReports()
                .enqueue(new Callback<RemoteReportPage>() {
                    @Override
                    public void onResponse(Call<RemoteReportPage> call,
                                           Response<RemoteReportPage> response) {
                        if (!response.isSuccessful()) {
                            callback.onHttpError(response.code());
                            return;
                        }
                        try {
                            callback.onSuccess(RemoteReportMapper.toComplaints(response.body()));
                        } catch (IllegalArgumentException exception) {
                            callback.onMalformedResponse(exception);
                        }
                    }

                    @Override
                    public void onFailure(Call<RemoteReportPage> call, Throwable throwable) {
                        callback.onFailure(throwable);
                    }
                });
    }

    /**
     * Fetches ALL reports from the backend for the Admin Operations Console.
     * Fetches up to 100 reports per page.
     */
    public void getAllReports(AdminReportListCallback callback) {
        apiService.getAllReports(1, 100)
                .enqueue(new Callback<AdminReportListResponse>() {
                    @Override
                    public void onResponse(Call<AdminReportListResponse> call,
                                           Response<AdminReportListResponse> response) {
                        if (!response.isSuccessful()) {
                            callback.onHttpError(response.code());
                            return;
                        }
                        AdminReportListResponse body = response.body();
                        List<RemoteReportResponse> items =
                                (body != null && body.items != null)
                                         ? body.items : Collections.emptyList();
                        int total = body != null ? body.total : 0;
                        callback.onSuccess(items, total);
                    }

                    @Override
                    public void onFailure(Call<AdminReportListResponse> call, Throwable throwable) {
                        Log.w(TAG, "Admin report fetch failed: " + throwable.getClass().getSimpleName());
                        callback.onFailure(throwable);
                    }
                });
    }

    public void updateReportStatus(String reportId, String status, StatusUpdateCallback callback) {
        if (TextUtils.isEmpty(reportId)) {
            callback.onConfigurationError("Remote report ID is not available");
            return;
        }

        apiService.updateReportStatus(
                reportId,
                new ReportStatusUpdate(status)
        ).enqueue(new Callback<RemoteReportResponse>() {
            @Override
            public void onResponse(Call<RemoteReportResponse> call,
                                   Response<RemoteReportResponse> response) {
                if (response.isSuccessful() && response.body() != null) {
                    callback.onSuccess(response.body());
                } else {
                    callback.onHttpError(response.code());
                }
            }

            @Override
            public void onFailure(Call<RemoteReportResponse> call, Throwable throwable) {
                callback.onConnectionFailure(throwable);
            }
        });
    }

    public void resolveReport(String reportId, String note, File imageFile, StatusUpdateCallback callback) {
        if (TextUtils.isEmpty(reportId)) {
            callback.onConfigurationError("Remote report ID is not available");
            return;
        }

        RequestBody notePart = note != null ? textPart(note) : null;
        MultipartBody.Part imagePart = imageFile != null ? buildResolutionImagePart(imageFile) : null;

        apiService.resolveReport(
                reportId,
                notePart,
                imagePart
        ).enqueue(new Callback<RemoteReportResponse>() {
            @Override
            public void onResponse(Call<RemoteReportResponse> call,
                                   Response<RemoteReportResponse> response) {
                if (response.isSuccessful() && response.body() != null) {
                    callback.onSuccess(response.body());
                } else {
                    callback.onHttpError(response.code());
                }
            }

            @Override
            public void onFailure(Call<RemoteReportResponse> call, Throwable throwable) {
                callback.onConnectionFailure(throwable);
            }
        });
    }

    /**
     * Fetches existing AI/VLM intelligence for a given report ID via GET.
     * If the backend returns 405 (Method Not Allowed), falls back to POST.
     */
    public void getAIIntelligence(String reportId, AIIntelligenceCallback callback) {
        if (TextUtils.isEmpty(reportId)) {
            Log.e(TAG, "[GET AI] Configuration error: Report ID is not available for AI analysis");
            callback.onConfigurationError("Report ID is not available for AI analysis");
            return;
        }

        Call<AIIntelligenceResponse> call = apiService.getAIIntelligence(reportId);
        Log.d(TAG, "[GET AI] Request started. reportId=" + reportId + ", URL=" + call.request().url());

        call.enqueue(new Callback<AIIntelligenceResponse>() {
            @Override
            public void onResponse(Call<AIIntelligenceResponse> call,
                                   Response<AIIntelligenceResponse> response) {
                Log.d(TAG, "[GET AI] HTTP response code=" + response.code() + ", isSuccessful=" + response.isSuccessful() + " for reportId=" + reportId);
                if (response.isSuccessful() && response.body() != null) {
                    callback.onSuccess(response.body());
                } else if (response.code() == 405) {
                    // Fallback to POST if GET is not supported by current server instance
                    Log.i(TAG, "[GET AI] Server returned 405 Method Not Allowed. Falling back to POST analyze-report for reportId=" + reportId);
                    reRunAIAnalysis(reportId, callback);
                } else {
                    String errBody = "";
                    try {
                        if (response.errorBody() != null) errBody = response.errorBody().string();
                    } catch (Exception ignored) {}
                    Log.e(TAG, "[GET AI] HTTP error code=" + response.code() + ", errorBody=" + errBody);
                    callback.onHttpError(response.code());
                }
            }

            @Override
            public void onFailure(Call<AIIntelligenceResponse> call, Throwable throwable) {
                Log.e(TAG, "[GET AI] Request failed. reportId=" + reportId + ", URL=" + call.request().url()
                        + ", error=" + throwable.getMessage(), throwable);
                callback.onFailure(throwable);
            }
        });
    }

    /**
     * Explicitly triggers or re-runs AI/VLM analysis for a given report ID.
     * Calls POST /api/v1/ai/analyze-report/{reportId}
     */
    public void reRunAIAnalysis(String reportId, AIIntelligenceCallback callback) {
        if (TextUtils.isEmpty(reportId)) {
            Log.e(TAG, "[POST AI Re-run] Configuration error: Report ID is not available for AI analysis");
            callback.onConfigurationError("Report ID is not available for AI analysis");
            return;
        }

        Call<AIIntelligenceResponse> call = apiService.analyzeReport(reportId);
        Log.d(TAG, "[POST AI Re-run] Request started. reportId=" + reportId + ", URL=" + call.request().url());

        call.enqueue(new Callback<AIIntelligenceResponse>() {
            @Override
            public void onResponse(Call<AIIntelligenceResponse> call,
                                   Response<AIIntelligenceResponse> response) {
                Log.d(TAG, "[POST AI Re-run] HTTP response code=" + response.code() + ", isSuccessful=" + response.isSuccessful() + " for reportId=" + reportId);
                if (response.isSuccessful() && response.body() != null) {
                    callback.onSuccess(response.body());
                } else {
                    String errBody = "";
                    try {
                        if (response.errorBody() != null) errBody = response.errorBody().string();
                    } catch (Exception ignored) {}
                    Log.e(TAG, "[POST AI Re-run] HTTP error code=" + response.code() + ", errorBody=" + errBody);
                    callback.onHttpError(response.code());
                }
            }

            @Override
            public void onFailure(Call<AIIntelligenceResponse> call, Throwable throwable) {
                Log.e(TAG, "[POST AI Re-run] Request failed. reportId=" + reportId + ", URL=" + call.request().url()
                        + ", error=" + throwable.getMessage(), throwable);
                callback.onFailure(throwable);
            }
        });
    }

    private RequestBody textPart(String value) {
        return RequestBody.create(TEXT_PLAIN, value);
    }

    private MultipartBody.Part buildImagePart(File imageFile) {
        if (imageFile == null || !imageFile.isFile()) return null;

        String guessedType = URLConnection.guessContentTypeFromName(imageFile.getName());
        MediaType imageType = guessedType != null && guessedType.startsWith("image/")
                ? MediaType.parse(guessedType) : JPEG;
        RequestBody imageBody = RequestBody.create(imageType, imageFile);
        return MultipartBody.Part.createFormData("image", imageFile.getName(), imageBody);
    }

    private MultipartBody.Part buildResolutionImagePart(File imageFile) {
        if (imageFile == null || !imageFile.isFile()) return null;

        String guessedType = URLConnection.guessContentTypeFromName(imageFile.getName());
        MediaType imageType = guessedType != null && guessedType.startsWith("image/")
                ? MediaType.parse(guessedType) : JPEG;
        RequestBody imageBody = RequestBody.create(imageType, imageFile);
        return MultipartBody.Part.createFormData("resolution_image", imageFile.getName(), imageBody);
    }
}
