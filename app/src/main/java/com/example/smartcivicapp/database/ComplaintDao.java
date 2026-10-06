package com.example.smartcivicapp.database;

import androidx.room.Dao;
import androidx.room.Insert;
import androidx.room.OnConflictStrategy;
import androidx.room.Query;
import androidx.room.Update;

import com.example.smartcivicapp.entities.Complaint;

import java.util.List;

/**
 * ComplaintDao — all database operations for Complaint entity.
 *
 * NEW QUERIES:
 *  - getComplaintsByStatus()      : filter panel
 *  - getComplaintsByIssueType()   : filter panel
 *  - getComplaintsByWard()        : area risk analysis
 *  - getPendingCount()            : analytics card
 *  - getResolvedCount()           : analytics card
 *  - getInProgressCount()         : analytics card
 *  - getAvgResolutionTime()       : analytics card
 *  - getComplaintsNear()          : repeat detection
 *  - getHighRiskWards()           : decision support panel
 *  - updateAfterImage()           : before/after image feature
 *  - upvoteComplaint()            : citizen upvote
 *  - updateRiskAndRepeat()        : risk analysis
 *  - updateTimeline()             : timeline tracking
 */
@Dao
public interface ComplaintDao {

    // ===================== INSERT / UPDATE =====================

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    long insertComplaint(Complaint complaint);

    @Update
    void updateComplaint(Complaint complaint);

    @Query("UPDATE Complaint SET remoteReportId = :remoteReportId WHERE id = :id")
    void updateRemoteReportId(int id, String remoteReportId);

    @Query("UPDATE Complaint SET status = :status WHERE id = :id")
    void updateStatus(int id, String status);

    @Query("UPDATE Complaint SET resolvedAt = :resolvedAt WHERE id = :id")
    void setResolvedAt(int id, long resolvedAt);

    @Query("UPDATE Complaint SET afterImagePath = :path WHERE id = :id")
    void updateAfterImage(int id, String path);

    @Query("UPDATE Complaint SET upvoteCount = upvoteCount + 1 WHERE id = :id")
    void upvoteComplaint(int id);

    @Query("UPDATE Complaint SET isRepeat = :repeat, riskLevel = :risk WHERE id = :id")
    void updateRiskAndRepeat(int id, boolean repeat, String risk);

    @Query("UPDATE Complaint SET timelineJson = :timeline WHERE id = :id")
    void updateTimeline(int id, String timeline);

    @Query("UPDATE Complaint SET citizenEmail = :email, citizenName = :name WHERE id = :id")
    void updateCitizenInfo(int id, String email, String name);

    // ===================== SELECT ALL =====================

    @Query("SELECT * FROM Complaint ORDER BY createdAt DESC")
    List<Complaint> getAllComplaints();

    @Query("SELECT * FROM Complaint WHERE id = :id LIMIT 1")
    Complaint getComplaintById(int id);

    @Query("SELECT * FROM Complaint WHERE remoteReportId = :remoteReportId LIMIT 1")
    Complaint getComplaintByRemoteId(String remoteReportId);

    // ===================== FILTER QUERIES =====================

    @Query("SELECT * FROM Complaint WHERE status = :status ORDER BY createdAt DESC")
    List<Complaint> getComplaintsByStatus(String status);

    @Query("SELECT * FROM Complaint WHERE issueType = :type ORDER BY createdAt DESC")
    List<Complaint> getComplaintsByIssueType(String type);

    @Query("SELECT * FROM Complaint WHERE ward = :ward ORDER BY createdAt DESC")
    List<Complaint> getComplaintsByWard(String ward);

    @Query("SELECT * FROM Complaint WHERE status = :status AND issueType = :type ORDER BY createdAt DESC")
    List<Complaint> getComplaintsByStatusAndType(String status, String type);

    // ===================== ANALYTICS =====================

    @Query("SELECT COUNT(*) FROM Complaint")
    int getTotalCount();

    @Query("SELECT COUNT(*) FROM Complaint WHERE status = 'Pending'")
    int getPendingCount();

    @Query("SELECT COUNT(*) FROM Complaint WHERE status = 'In Progress'")
    int getInProgressCount();

    @Query("SELECT COUNT(*) FROM Complaint WHERE status = 'Resolved'")
    int getResolvedCount();

    /** Returns average resolution time in milliseconds, or 0 if none resolved. */
    @Query("SELECT AVG(resolvedAt - createdAt) FROM Complaint WHERE resolvedAt > 0")
    long getAvgResolutionTimeMs();

    @Query("SELECT COUNT(*) FROM Complaint WHERE issueType = :type")
    int getCountByType(String type);

    @Query("SELECT COUNT(*) FROM Complaint WHERE isRepeat = 1")
    int getRepeatCount();

    // ===================== REPEAT / RISK DETECTION =====================

    /**
     * Returns complaints within approx 100m of given lat/lng.
     * Uses bounding box (0.001 degree ≈ 111m) for efficiency.
     */
    @Query("SELECT * FROM Complaint WHERE " +
           "latitude  BETWEEN :lat - 0.001 AND :lat + 0.001 AND " +
           "longitude BETWEEN :lng - 0.001 AND :lng + 0.001 AND " +
           "issueType = :issueType AND id != :excludeId")
    List<Complaint> getComplaintsNear(double lat, double lng,
                                      String issueType, int excludeId);

    /** Returns ward names that have 3 or more complaints — high-risk zones. */
    @Query("SELECT ward FROM Complaint " +
           "WHERE ward IS NOT NULL AND ward != '' " +
           "GROUP BY ward HAVING COUNT(*) >= 3 " +
           "ORDER BY COUNT(*) DESC")
    List<String> getHighRiskWards();

    /** Full ward analysis: ward name + complaint count. */
    @Query("SELECT ward, COUNT(*) as cnt FROM Complaint " +
           "WHERE ward IS NOT NULL AND ward != '' " +
           "GROUP BY ward ORDER BY cnt DESC")
    List<WardCount> getWardAnalysis();

    /** Returns all unique issue types in the DB. */
    @Query("SELECT DISTINCT issueType FROM Complaint WHERE issueType IS NOT NULL")
    List<String> getAllIssueTypes();

    // ===================== DELETE =====================

    @Query("DELETE FROM Complaint WHERE id = :id")
    void deleteComplaintById(int id);
}
