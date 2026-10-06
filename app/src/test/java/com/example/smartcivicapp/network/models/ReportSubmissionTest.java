package com.example.smartcivicapp.network.models;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import org.junit.Test;

public class ReportSubmissionTest {
    @Test
    public void retainsValidatedValuesWithoutAnImage() {
        ReportSubmission submission = new ReportSubmission(
                "Road Damage", "Pothole", 28.6139, 77.2090,
                "2026-09-12T10:30:00+05:30", "medium", null);

        assertEquals("Road Damage", submission.getIssueCategory());
        assertEquals("medium", submission.getSeverity());
        assertNull(submission.getImageFile());
    }
}
