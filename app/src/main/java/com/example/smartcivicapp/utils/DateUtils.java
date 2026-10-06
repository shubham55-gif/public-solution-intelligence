package com.example.smartcivicapp.utils;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.TimeUnit;

/**
 * DateUtils — date/time formatting helpers used across the app.
 */
public class DateUtils {

    /** Returns "dd MMM yyyy" format, e.g. "12 Nov 2024". */
    public static String formatDate(long ms) {
        return new SimpleDateFormat("dd MMM yyyy", Locale.getDefault()).format(new Date(ms));
    }

    /** Returns "hh:mm a" format, e.g. "10:35 AM". */
    public static String formatTime(long ms) {
        return new SimpleDateFormat("hh:mm a", Locale.getDefault()).format(new Date(ms));
    }

    /** Returns "dd MMM, hh:mm a" format. */
    public static String formatDateTime(long ms) {
        return new SimpleDateFormat("dd MMM, hh:mm a", Locale.getDefault()).format(new Date(ms));
    }

    /**
     * Returns human-readable duration from a timestamp to now.
     * E.g. "2 days 4 hrs" or "35 mins"
     */
    public static String timeAgo(long ms) {
        long diff = System.currentTimeMillis() - ms;
        long days    = TimeUnit.MILLISECONDS.toDays(diff);
        long hours   = TimeUnit.MILLISECONDS.toHours(diff) % 24;
        long minutes = TimeUnit.MILLISECONDS.toMinutes(diff) % 60;

        if (days > 0)    return days + "d " + hours + "h ago";
        if (hours > 0)   return hours + "h " + minutes + "m ago";
        if (minutes > 0) return minutes + "m ago";
        return "just now";
    }

    /**
     * Returns average resolution time as a readable string.
     * Input is in milliseconds.
     */
    public static String formatAvgResolutionTime(long ms) {
        if (ms <= 0) return "N/A";
        long days  = TimeUnit.MILLISECONDS.toDays(ms);
        long hours = TimeUnit.MILLISECONDS.toHours(ms) % 24;
        if (days > 0) return days + " day" + (days > 1 ? "s" : "");
        if (hours > 0) return hours + " hr" + (hours > 1 ? "s" : "");
        return "< 1 hr";
    }

    /**
     * Formats an ISO-8601 timestamp string (e.g. "2026-10-06T00:22:00Z" or "2026-10-06T00:22:00+00:00")
     * or numeric epoch string into "06 Oct 2026, 12:22 AM".
     */
    public static String formatIsoTimestamp(String iso) {
        if (iso == null || iso.trim().isEmpty() || "null".equalsIgnoreCase(iso.trim())) {
            return "—";
        }
        String trimmed = iso.trim();
        try {
            // Try parsing as ISO OffsetDateTime
            java.time.OffsetDateTime dt = java.time.OffsetDateTime.parse(trimmed);
            long ms = dt.toInstant().toEpochMilli();
            return new SimpleDateFormat("dd MMM yyyy, hh:mm a", Locale.getDefault()).format(new Date(ms));
        } catch (Exception e1) {
            try {
                // Try parsing as ISO Instant
                java.time.Instant inst = java.time.Instant.parse(trimmed);
                return new SimpleDateFormat("dd MMM yyyy, hh:mm a", Locale.getDefault()).format(new Date(inst.toEpochMilli()));
            } catch (Exception e2) {
                try {
                    // Try parsing as numeric epoch ms
                    long ms = Long.parseLong(trimmed);
                    return new SimpleDateFormat("dd MMM yyyy, hh:mm a", Locale.getDefault()).format(new Date(ms));
                } catch (Exception e3) {
                    return trimmed;
                }
            }
        }
    }
}
