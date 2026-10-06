package com.example.smartcivicapp.network.models;

import com.google.gson.annotations.SerializedName;

public class UserProfileResponse {
    @SerializedName("user_id")
    public String userId;

    @SerializedName("name")
    public String name;

    @SerializedName("email")
    public String email;

    @SerializedName("role")
    public String role;

    @SerializedName("phone")
    public String phone;

    @SerializedName("member_since")
    public String memberSince;

    @SerializedName("total_reports")
    public int totalReports;

    @SerializedName("pending_reports")
    public int pendingReports;

    @SerializedName("in_progress_reports")
    public int inProgressReports;

    @SerializedName("resolved_reports")
    public int resolvedReports;
}
