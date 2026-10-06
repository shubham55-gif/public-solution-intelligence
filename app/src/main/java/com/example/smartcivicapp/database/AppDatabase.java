package com.example.smartcivicapp.database;

import android.content.Context;

import androidx.room.Database;
import androidx.room.Room;
import androidx.room.RoomDatabase;

import com.example.smartcivicapp.entities.Complaint;

/**
 * AppDatabase — Room database singleton for the app.
 */
@Database(entities = {Complaint.class}, version = 2, exportSchema = false)
public abstract class AppDatabase extends RoomDatabase {

    private static volatile AppDatabase instance;
    private static final androidx.room.migration.Migration MIGRATION_1_2 =
            new androidx.room.migration.Migration(1, 2) {
                @Override
                public void migrate(androidx.sqlite.db.SupportSQLiteDatabase database) {
                    database.execSQL("ALTER TABLE Complaint ADD COLUMN remoteReportId TEXT");
                }
            };

    public abstract ComplaintDao complaintDao();

    public static AppDatabase getInstance(Context context) {
        if (instance == null) {
            synchronized (AppDatabase.class) {
                if (instance == null) {
                    instance = Room.databaseBuilder(
                                    context.getApplicationContext(),
                                    AppDatabase.class,
                                    "civic_db"
                            )
                            .allowMainThreadQueries()
                            .addMigrations(MIGRATION_1_2)
                            .fallbackToDestructiveMigration() // Prevent crash on schema change
                            .build();
                }

            }
        }
        return instance;
    }
}