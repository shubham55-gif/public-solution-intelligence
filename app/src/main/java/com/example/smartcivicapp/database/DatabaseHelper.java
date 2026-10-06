package com.example.smartcivicapp.database;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

/**
 * DatabaseHelper — SQLite helper for Auth tables.
 * Version 2 adds citizen_name retrieval for display in complaints.
 */
public class DatabaseHelper extends SQLiteOpenHelper {

    private static final String DATABASE_NAME    = "AuthDB.db";
    private static final int    DATABASE_VERSION = 2;

    public static final String ADMIN_TABLE    = "admin";
    public static final String ADMIN_ID       = "admin_id";
    public static final String ADMIN_USERNAME = "username";
    public static final String ADMIN_PASSWORD = "password";

    public static final String CITIZEN_TABLE    = "citizen";
    public static final String CITIZEN_ID       = "citizen_id";
    public static final String CITIZEN_NAME     = "name";
    public static final String CITIZEN_EMAIL    = "email";
    public static final String CITIZEN_PHONE    = "phone";
    public static final String CITIZEN_PASSWORD = "password";

    public DatabaseHelper(Context context) {
        super(context, DATABASE_NAME, null, DATABASE_VERSION);
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        db.execSQL(
            "CREATE TABLE " + ADMIN_TABLE + " (" +
            ADMIN_ID + " INTEGER PRIMARY KEY AUTOINCREMENT, " +
            ADMIN_USERNAME + " TEXT UNIQUE NOT NULL, " +
            ADMIN_PASSWORD + " TEXT NOT NULL)"
        );
        db.execSQL(
            "CREATE TABLE " + CITIZEN_TABLE + " (" +
            CITIZEN_ID + " INTEGER PRIMARY KEY AUTOINCREMENT, " +
            CITIZEN_NAME + " TEXT NOT NULL, " +
            CITIZEN_EMAIL + " TEXT UNIQUE NOT NULL, " +
            CITIZEN_PHONE + " TEXT UNIQUE NOT NULL, " +
            CITIZEN_PASSWORD + " TEXT NOT NULL)"
        );
        insertDefaultAdmin(db);
    }

    private void insertDefaultAdmin(SQLiteDatabase db) {
        ContentValues v = new ContentValues();
        v.put(ADMIN_USERNAME, "admin");
        v.put(ADMIN_PASSWORD, "admin123");
        db.insert(ADMIN_TABLE, null, v);
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        db.execSQL("DROP TABLE IF EXISTS " + ADMIN_TABLE);
        db.execSQL("DROP TABLE IF EXISTS " + CITIZEN_TABLE);
        onCreate(db);
    }

    public boolean checkAdminLogin(String username, String password) {
        SQLiteDatabase db = this.getReadableDatabase();
        Cursor cursor = null;
        try {
            cursor = db.rawQuery(
                "SELECT " + ADMIN_ID + " FROM " + ADMIN_TABLE +
                " WHERE username=? AND password=?",
                new String[]{username, password});
            return cursor.getCount() > 0;
        } finally {
            if (cursor != null) cursor.close();
        }
    }

    public boolean registerCitizen(String name, String email, String phone, String password) {
        SQLiteDatabase db = this.getWritableDatabase();
        Cursor cursor = null;
        try {
            cursor = db.rawQuery(
                "SELECT " + CITIZEN_ID + " FROM " + CITIZEN_TABLE +
                " WHERE email=? OR phone=?",
                new String[]{email, phone});
            if (cursor.getCount() > 0) return false;
        } finally {
            if (cursor != null) cursor.close();
        }
        ContentValues v = new ContentValues();
        v.put(CITIZEN_NAME, name);
        v.put(CITIZEN_EMAIL, email);
        v.put(CITIZEN_PHONE, phone);
        v.put(CITIZEN_PASSWORD, password);
        return db.insert(CITIZEN_TABLE, null, v) != -1;
    }

    public boolean checkCitizenLogin(String email, String password) {
        SQLiteDatabase db = this.getReadableDatabase();
        Cursor cursor = null;
        try {
            cursor = db.rawQuery(
                "SELECT " + CITIZEN_ID + " FROM " + CITIZEN_TABLE +
                " WHERE email=? AND password=?",
                new String[]{email, password});
            return cursor.getCount() > 0;
        } finally {
            if (cursor != null) cursor.close();
        }
    }

    /** Returns citizen's display name by email. */
    public String getCitizenName(String email) {
        SQLiteDatabase db = this.getReadableDatabase();
        Cursor cursor = null;
        try {
            cursor = db.rawQuery(
                "SELECT " + CITIZEN_NAME + " FROM " + CITIZEN_TABLE +
                " WHERE email=?",
                new String[]{email});
            if (cursor.moveToFirst()) return cursor.getString(0);
        } finally {
            if (cursor != null) cursor.close();
        }
        return "";
    }
}
