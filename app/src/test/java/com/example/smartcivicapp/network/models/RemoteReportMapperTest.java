package com.example.smartcivicapp.network.models;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import com.example.smartcivicapp.entities.Complaint;
import com.google.gson.Gson;

import org.junit.Test;

import java.util.List;

public class RemoteReportMapperTest {

    private final Gson gson = new Gson();

    @Test
    public void parsesAndMapsRemoteReportFields() {
        RemoteReportPage page = gson.fromJson(
                "{\"items\":[{\"id\":\"report-1\",\"issue_category\":\"Road Damage\","
                        + "\"description\":\"Pothole\",\"latitude\":28.6139,"
                        + "\"longitude\":77.209,\"reported_at\":\"2026-09-12T10:30:00+05:30\","
                        + "\"severity\":\"high\",\"status\":\"pending\","
                        + "\"image_path\":\"uploads/road.jpg\"}],\"page\":1,"
                        + "\"page_size\":20,\"total\":1,\"total_pages\":1}",
                RemoteReportPage.class);

        List<Complaint> complaints = RemoteReportMapper.toComplaints(page);

        assertEquals(1, complaints.size());
        assertEquals("Road Damage", complaints.get(0).issueType);
        assertEquals("Pothole", complaints.get(0).description);
        assertEquals("Pending", complaints.get(0).status);
        assertEquals("uploads/road.jpg", complaints.get(0).beforeImagePath);
        assertEquals(28.6139, complaints.get(0).latitude, 0.000001);
    }

    @Test
    public void mapsEmptyRemoteList() {
        RemoteReportPage page = gson.fromJson(
                "{\"items\":[],\"page\":1,\"page_size\":20,\"total\":0,\"total_pages\":0}",
                RemoteReportPage.class);

        assertTrue(RemoteReportMapper.toComplaints(page).isEmpty());
    }

    @Test(expected = IllegalArgumentException.class)
    public void rejectsMalformedRemoteList() {
        RemoteReportPage page = gson.fromJson(
                "{\"page\":1,\"page_size\":20,\"total\":1,\"total_pages\":1}",
                RemoteReportPage.class);

        RemoteReportMapper.toComplaints(page);
    }

    @Test
    public void normalizesRemoteStatusForExistingUi() {
        RemoteReportResponse remote = new RemoteReportResponse();
        remote.id = "report-2";
        remote.issue_category = "Garbage Overflow";
        remote.description = "Overflowing bin";
        remote.latitude = 28.6;
        remote.longitude = 77.2;
        remote.reported_at = "2026-09-12T10:30:00Z";
        remote.status = "in_progress";

        assertEquals("In Progress", RemoteReportMapper.toComplaint(remote).status);
    }

    @Test(expected = IllegalArgumentException.class)
    public void rejectsUnknownRemoteStatus() {
        RemoteReportResponse remote = new RemoteReportResponse();
        remote.id = "report-3";
        remote.issue_category = "Road Damage";
        remote.description = "Pothole";
        remote.latitude = 28.6;
        remote.longitude = 77.2;
        remote.reported_at = "2026-09-12T10:30:00Z";
        remote.status = "unknown";

        RemoteReportMapper.toComplaint(remote);
    }

    @Test(expected = IllegalArgumentException.class)
    public void rejectsNonFiniteCoordinates() {
        RemoteReportResponse remote = new RemoteReportResponse();
        remote.id = "report-4";
        remote.issue_category = "Road Damage";
        remote.description = "Pothole";
        remote.latitude = Double.NaN;
        remote.longitude = 77.2;
        remote.reported_at = "2026-09-12T10:30:00Z";
        remote.status = "pending";

        RemoteReportMapper.toComplaint(remote);
    }
}
