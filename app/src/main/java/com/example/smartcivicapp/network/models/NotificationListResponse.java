package com.example.smartcivicapp.network.models;

import com.google.gson.annotations.SerializedName;
import java.util.List;

public class NotificationListResponse {
    @SerializedName("unread_count")
    public int unreadCount;

    @SerializedName("notifications")
    public List<NotificationItem> notifications;
}
