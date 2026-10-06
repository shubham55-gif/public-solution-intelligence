package com.example.smartcivicapp;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

import androidx.core.app.NotificationCompat;

/**
 * NotificationHelper — posts notifications for status updates and new complaints.
 *
 * NEW:
 *  - showStatusUpdateNotification() : citizen is notified when admin updates status
 *  - showNewComplaintNotification()  : admin is notified when citizen submits
 *  - Clickable PendingIntent opens ComplaintListActivity
 */
public class NotificationHelper {

    private static final String CHANNEL_STATUS  = "civic_status_channel";
    private static final String CHANNEL_ADMIN   = "civic_admin_channel";

    /** Notifies admin of a newly submitted complaint. */
    public static void showNewComplaintNotification(Context context, String issueType, String ward) {
        NotificationManager manager = getManager(context);
        if (manager == null) return;

        createChannel(manager, CHANNEL_ADMIN, "Admin Alerts",
                NotificationManager.IMPORTANCE_HIGH);

        Intent intent = new Intent(context, ComplaintListActivity.class);
        PendingIntent pi = PendingIntent.getActivity(context, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL_ADMIN)
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle("New Complaint Submitted")
                .setContentText(issueType + (ward != null && !ward.isEmpty() ? " in " + ward : ""))
                .setStyle(new NotificationCompat.BigTextStyle()
                        .bigText("A citizen has reported: " + issueType +
                                (ward != null && !ward.isEmpty() ? " in area: " + ward : "") +
                                ". Tap to review."))
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setContentIntent(pi)
                .setAutoCancel(true);

        manager.notify((int) System.currentTimeMillis(), builder.build());
    }

    /**
     * Notifies citizen that their complaint status has been updated.
     *
     * @param complaintId used to open detail screen on tap
     * @param issueType   complaint category
     * @param newStatus   updated status string
     */
    public static void showStatusUpdateNotification(Context context,
                                                    int complaintId,
                                                    String issueType,
                                                    String newStatus) {

        NotificationManager manager = getManager(context);
        if (manager == null) return;

        createChannel(manager, CHANNEL_STATUS, "Status Updates",
                NotificationManager.IMPORTANCE_DEFAULT);

        // Clicking opens ComplaintListActivity
        Intent intent = new Intent(context, ComplaintListActivity.class);
        PendingIntent pi = PendingIntent.getActivity(context, complaintId, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        String emoji = "Resolved".equalsIgnoreCase(newStatus) ? "✅" :
                       "In Progress".equalsIgnoreCase(newStatus) ? "🔧" : "🕐";

        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL_STATUS)
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle(emoji + " Complaint Status Updated")
                .setContentText("Your " + issueType + " report is now: " + newStatus)
                .setStyle(new NotificationCompat.BigTextStyle()
                        .bigText("Your complaint about '" + issueType +
                                "' has been updated to: " + newStatus +
                                ".\n\nTap to view details."))
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setContentIntent(pi)
                .setAutoCancel(true);

        manager.notify(complaintId, builder.build());
    }

    /** Generic notification — used for general alerts. */
    public static void showNotification(Context context, String title, String message) {
        NotificationManager manager = getManager(context);
        if (manager == null) return;

        createChannel(manager, CHANNEL_STATUS, "Civic Notifications",
                NotificationManager.IMPORTANCE_DEFAULT);

        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL_STATUS)
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle(title)
                .setContentText(message)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setAutoCancel(true);

        manager.notify((int) System.currentTimeMillis(), builder.build());
    }

    // ---- private helpers ----

    private static NotificationManager getManager(Context context) {
        return (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
    }

    private static void createChannel(NotificationManager manager,
                                      String id, String name, int importance) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            if (manager.getNotificationChannel(id) == null) {
                manager.createNotificationChannel(
                        new NotificationChannel(id, name, importance));
            }
        }
    }
}
