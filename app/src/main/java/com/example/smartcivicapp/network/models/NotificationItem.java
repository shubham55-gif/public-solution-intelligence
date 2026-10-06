package com.example.smartcivicapp.network.models;

import com.google.gson.annotations.SerializedName;

public class NotificationItem {
    @SerializedName("id")
    public String id;

    @SerializedName("report_id")
    public String reportId;

    @SerializedName("title")
    public String title;

    @SerializedName("message")
    public String message;

    @SerializedName("type")
    public String type;

    @SerializedName("is_read")
    public boolean isRead;

    @SerializedName("created_at")
    public String createdAt;
}
