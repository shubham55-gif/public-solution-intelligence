package com.example.smartcivicapp.utils;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/**
 * TimelineHelper — encodes and decodes the complaint timeline string.
 *
 * Format stored in DB:
 *   "Reported:1700000000|In Progress:1700001000|Resolved:1700002000"
 *
 * Each entry is "EventName:UnixTimestampMs".
 */
public class TimelineHelper {

    public static class TimelineEvent {
        public String eventName;
        public long   timestamp;

        public TimelineEvent(String eventName, long timestamp) {
            this.eventName = eventName;
            this.timestamp = timestamp;
        }

        /** Returns formatted date string like "12 Nov 2024, 10:35 AM" */
        public String getFormattedTime() {
            SimpleDateFormat sdf = new SimpleDateFormat(
                    "dd MMM yyyy, hh:mm a", Locale.getDefault());
            return sdf.format(new Date(timestamp));
        }
    }

    /** Parses a stored timeline string into a list of events. */
    public static List<TimelineEvent> parse(String timelineJson) {
        List<TimelineEvent> events = new ArrayList<>();
        if (timelineJson == null || timelineJson.isEmpty()) return events;

        String[] parts = timelineJson.split("\\|");
        for (String part : parts) {
            String[] kv = part.split(":");
            if (kv.length == 2) {
                try {
                    events.add(new TimelineEvent(kv[0], Long.parseLong(kv[1])));
                } catch (NumberFormatException ignored) {}
            }
        }
        return events;
    }

    /**
     * Appends a new event to an existing timeline string.
     *
     * @param existing existing timeline string (can be empty)
     * @param event    new event name (e.g. "In Progress")
     * @return updated timeline string
     */
    public static String appendEvent(String existing, String event) {
        String entry = event + ":" + System.currentTimeMillis();
        if (existing == null || existing.isEmpty()) return entry;
        return existing + "|" + entry;
    }

    /** Builds an initial timeline string with "Reported" event at given time. */
    public static String createInitial(long createdAt) {
        return "Reported:" + createdAt;
    }
}
