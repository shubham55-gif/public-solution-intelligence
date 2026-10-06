package com.example.smartcivicapp.network.models;

import java.util.List;

/** Gson model for the FastAPI paginated admin report-list response. */
public class AdminReportListResponse {
    public List<RemoteReportResponse> items;
    public int total;
    public int page;
    public int page_size;
}
