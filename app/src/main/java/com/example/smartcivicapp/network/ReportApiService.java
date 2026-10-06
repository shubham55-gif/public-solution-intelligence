package com.example.smartcivicapp.network;

import com.example.smartcivicapp.network.models.AdminReportListResponse;
import com.example.smartcivicapp.network.models.AIIntelligenceResponse;
import com.example.smartcivicapp.network.models.RemoteReportResponse;
import com.example.smartcivicapp.network.models.RemoteReportPage;

import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Multipart;
import retrofit2.http.POST;
import retrofit2.http.Part;
import retrofit2.http.PATCH;
import retrofit2.http.Path;
import retrofit2.http.Body;
import retrofit2.http.Query;

/** Retrofit contract for the Public Solution Intelligence Reports API. */
public interface ReportApiService {

    /* ── Citizen ── */

    @GET("api/v1/reports/{reportId}")
    Call<RemoteReportResponse> getReport(
            @Path("reportId") String reportId
    );

    @GET("api/v1/reports/my")
    Call<RemoteReportPage> getMyReports();

    @Multipart
    @POST("api/v1/reports")
    Call<RemoteReportResponse> createReport(
            @Part("issue_category") RequestBody issueCategory,
            @Part("description") RequestBody description,
            @Part("latitude") RequestBody latitude,
            @Part("longitude") RequestBody longitude,
            @Part("reported_at") RequestBody reportedAt,
            @Part("severity") RequestBody severity,
            @Part MultipartBody.Part image
    );

    /* ── Admin: all reports ── */

    /**
     * Fetch all reports (admin/authority view).
     * GET /api/v1/reports?page=1&page_size=100
     */
    @GET("api/v1/reports")
    Call<AdminReportListResponse> getAllReports(
            @Query("page") int page,
            @Query("page_size") int pageSize
    );

    /* ── Status update (admin only) ── */

    @PATCH("api/v1/admin/reports/{reportId}/status")
    Call<RemoteReportResponse> updateReportStatus(
            @Path("reportId") String reportId,
            @Body com.example.smartcivicapp.network.models.ReportStatusUpdate statusUpdate
    );

    /* ── Resolve update (admin only) ── */

    @Multipart
    @POST("api/v1/admin/reports/{reportId}/resolve")
    Call<RemoteReportResponse> resolveReport(
            @Path("reportId") String reportId,
            @Part("resolution_note") RequestBody resolutionNote,
            @Part MultipartBody.Part resolutionImage
    );

    /* ── AI / Intelligence ── */

    /**
     * Fetch existing AI/VLM analysis for a single report.
     * GET /api/v1/ai/analyze-report/{reportId}
     */
    @GET("api/v1/ai/analyze-report/{reportId}")
    Call<AIIntelligenceResponse> getAIIntelligence(
            @Path("reportId") String reportId
    );

    /**
     * Trigger or re-run AI/VLM analysis for a single report.
     * POST /api/v1/ai/analyze-report/{reportId}
     */
    @POST("api/v1/ai/analyze-report/{reportId}")
    Call<AIIntelligenceResponse> analyzeReport(
            @Path("reportId") String reportId
    );

    /* ── Auth ── */

    @POST("api/v1/auth/login")
    Call<com.example.smartcivicapp.network.models.TokenResponse> login(
            @Body com.example.smartcivicapp.network.models.LoginRequest request
    );

    @POST("api/v1/auth/register")
    Call<com.example.smartcivicapp.network.models.TokenResponse> register(
            @Body com.example.smartcivicapp.network.models.RegisterRequest request
    );

    @GET("api/v1/auth/profile")
    Call<com.example.smartcivicapp.network.models.UserProfileResponse> getProfile();

    @GET("api/v1/auth/admin/stats")
    Call<com.example.smartcivicapp.network.models.AdminStatsResponse> getAdminStats();

    /* ── In-App Notifications ── */

    @GET("api/v1/notifications")
    Call<com.example.smartcivicapp.network.models.NotificationListResponse> getNotifications();

    @POST("api/v1/notifications/{id}/read")
    Call<okhttp3.ResponseBody> markNotificationRead(@Path("id") String notificationId);

    @POST("api/v1/notifications/read-all")
    Call<okhttp3.ResponseBody> markAllNotificationsRead();
}
