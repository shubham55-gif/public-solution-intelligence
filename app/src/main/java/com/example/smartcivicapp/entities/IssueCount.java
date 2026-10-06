package com.example.smartcivicapp.entities;

/**
 * IssueCount — lightweight POJO used by AnalysisActivity
 * to hold per-type complaint counts returned from the DB.
 *
 * IMPROVEMENTS:
 *  - Constructor added for convenience
 *  - toString() for easy debug printing
 */
public class IssueCount {

    public String issueType;
    public int    count;

    public IssueCount() {}

    public IssueCount(String issueType, int count) {
        this.issueType = issueType;
        this.count     = count;
    }

    @Override
    public String toString() {
        return issueType + ": " + count;
    }
}