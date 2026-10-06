package com.example.smartcivicapp.network.models;

/** Request body for authority report status changes. */
public final class ReportStatusUpdate {
    public final String status;

    public ReportStatusUpdate(String status) {
        this.status = status;
    }
}
