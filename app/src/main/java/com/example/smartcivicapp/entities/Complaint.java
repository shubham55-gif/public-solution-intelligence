package com.example.smartcivicapp.entities;

import androidx.room.Entity;
import androidx.room.PrimaryKey;

/**
 * Complaint — Room entity with full feature support.
 *
 * NEW FIELDS:
 *  - citizenEmail       : links complaint to citizen for notifications
 *  - citizenName        : display name in admin view
 *  - beforeImagePath    : path to citizen-uploaded issue image
 *  - afterImagePath     : path to admin-uploaded resolved image
 *  - resolvedAt         : timestamp of resolution (for avg time analytics)
 *  - upvoteCount        : citizens can upvote repeated issues
 *  - ward               : area/ward name for risk analysis
 *  - timelineJson       : JSON string storing timeline events
 *  - riskLevel          : "Low" / "Medium" / "High" — computed field
 *  - isRepeat           : true if another complaint exists within 100m
 */
@Entity(tableName = "Complaint")
public class Complaint {

    @PrimaryKey(autoGenerate = true)
    public int id;
    public String remoteReportId;

    // ---- Core fields ----
    public String issueType;
    public String description;
    public String status = "Pending";

    // ---- Location ----
    public double latitude;
    public double longitude;
    public String ward;           // Area / ward label

    // ---- Citizen info ----
    public String citizenEmail;
    public String citizenName;

    // ---- Images ----
    public String beforeImagePath; // File path to before-photo
    public String afterImagePath;  // File path to after-photo (set by admin)

    // ---- Timestamps ----
    public long createdAt;
    public long resolvedAt;        // 0 = not yet resolved

    // ---- Analytics ----
    public int  upvoteCount = 0;
    public boolean isRepeat = false;
    public String riskLevel = "Low"; // "Low" | "Medium" | "High"

    // ---- Timeline ----
    // Stored as pipe-separated: "Reported:1700000000|In Progress:1700001000|Resolved:1700002000"
    public String timelineJson = "";
}
