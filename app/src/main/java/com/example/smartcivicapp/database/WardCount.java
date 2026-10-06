package com.example.smartcivicapp.database;

/**
 * WardCount — lightweight POJO returned by the ward analysis query.
 * Room maps the result of getWardAnalysis() to this class.
 */
public class WardCount {
    public String ward;
    public int    cnt;
}
