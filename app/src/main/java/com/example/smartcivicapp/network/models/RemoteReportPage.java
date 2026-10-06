package com.example.smartcivicapp.network.models;

import java.util.List;

/** Gson model for the paginated FastAPI citizen report list response. */
public class RemoteReportPage {
    public List<RemoteReportResponse> items;
    public int page;
    public int page_size;
    public int total;
    public int total_pages;
}
