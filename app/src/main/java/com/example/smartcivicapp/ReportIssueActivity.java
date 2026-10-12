package com.example.smartcivicapp;

import android.Manifest;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.text.TextUtils;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.example.smartcivicapp.database.AppDatabase;
import com.example.smartcivicapp.entities.Complaint;
import com.example.smartcivicapp.network.models.RemoteReportResponse;
import com.example.smartcivicapp.network.models.ReportSubmission;
import com.example.smartcivicapp.repositories.ReportRepository;
import com.example.smartcivicapp.utils.LocaleHelper;
import com.example.smartcivicapp.utils.RiskAnalyzer;
import com.example.smartcivicapp.utils.TimelineHelper;
import com.google.android.gms.location.FusedLocationProviderClient;
import com.google.android.gms.location.LocationServices;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;

/**
 * ReportIssueActivity — citizen submits a complaint.
 */
public class ReportIssueActivity extends AppCompatActivity {

    private static final int REQ_CAMERA   = 101;
    private static final int REQ_LOCATION = 102;

    private Spinner   spinnerIssue;
    private EditText  etDescription, etWard;
    private ImageView ivImage;
    private TextView  tvLocation, tvNoImageHint;
    private Button    btnCapture, btnSubmit;

    private Bitmap capturedBitmap;
    private String savedImagePath = "";

    private double latitude  = 0;
    private double longitude = 0;

    private FusedLocationProviderClient locationClient;
    private PrefManager pref;
    private ReportRepository reportRepository;
    private CharSequence submitButtonText;
    private boolean isSubmitting = false;

    private final ActivityResultLauncher<Intent> cameraLauncher =
            registerForActivityResult(
                    new ActivityResultContracts.StartActivityForResult(),
                    result -> {
                        if (result.getResultCode() == RESULT_OK
                                && result.getData() != null) {
                            Bundle extras = result.getData().getExtras();
                            if (extras != null && extras.containsKey("data")) {
                                capturedBitmap = (Bitmap) extras.get("data");
                                if (capturedBitmap != null) {
                                    ivImage.setImageBitmap(capturedBitmap);
                                    if (tvNoImageHint != null) tvNoImageHint.setVisibility(View.GONE);
                                }
                            }
                        }
                    });

    @Override
    protected void attachBaseContext(Context newBase) {
        super.attachBaseContext(LocaleHelper.onAttach(newBase));
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_report_issue);

        pref          = new PrefManager(this);
        spinnerIssue  = findViewById(R.id.spinnerIssue);
        etDescription = findViewById(R.id.etDescription);
        etWard        = findViewById(R.id.etWard);
        ivImage       = findViewById(R.id.ivImage);
        tvLocation    = findViewById(R.id.tvLocation);
        tvNoImageHint = findViewById(R.id.tvNoImageHint);
        btnCapture = findViewById(R.id.btnCapture);
        btnSubmit  = findViewById(R.id.btnSubmit);
        submitButtonText = btnSubmit.getText();
        reportRepository = new ReportRepository(this);

        ArrayAdapter<CharSequence> issueAdapter = ArrayAdapter.createFromResource(
                this, R.array.issue_categories, android.R.layout.simple_spinner_item);
        issueAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinnerIssue.setAdapter(issueAdapter);
        spinnerIssue.setPrompt(getString(R.string.cat_select));

        locationClient = LocationServices.getFusedLocationProviderClient(this);
        fetchLocation();

        btnCapture.setOnClickListener(v -> checkAndOpenCamera());
        btnSubmit.setOnClickListener(v  -> submitComplaint());
    }

    private static final String[] BACKEND_CATEGORIES = {
        "",
        "Road Damage",
        "Garbage Overflow",
        "Water Leakage",
        "Street Light Issue"
    };

    private void checkAndOpenCamera() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED) {
            openCamera();
        } else {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.CAMERA}, REQ_CAMERA);
        }
    }

    private void openCamera() {
        try {
            Intent i = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            cameraLauncher.launch(i);
        } catch (Exception e) {
            Toast.makeText(this, R.string.err_camera_open, Toast.LENGTH_SHORT).show();
        }
    }

    private void fetchLocation() {
        tvLocation.setText(R.string.hint_fetching_location);
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.ACCESS_FINE_LOCATION}, REQ_LOCATION);
            return;
        }
        locationClient.getLastLocation().addOnSuccessListener(loc -> {
            if (loc != null) {
                latitude  = loc.getLatitude();
                longitude = loc.getLongitude();
                tvLocation.setText(String.format("📍 %.5f, %.5f", latitude, longitude));
            } else {
                tvLocation.setText(R.string.msg_location_unavailable);
            }
        });
    }

    private void submitComplaint() {
        if (isSubmitting) return;

        String description = etDescription.getText().toString().trim();
        String ward        = etWard != null ? etWard.getText().toString().trim() : "";
        int selectedPos    = spinnerIssue.getSelectedItemPosition();

        if (selectedPos <= 0 || selectedPos >= BACKEND_CATEGORIES.length) {
            Toast.makeText(this, R.string.err_select_issue_type, Toast.LENGTH_SHORT).show();
            spinnerIssue.requestFocus();
            spinnerIssue.performClick();
            return;
        }

        if (TextUtils.isEmpty(description)) {
            etDescription.setError(getString(R.string.err_enter_description));
            etDescription.requestFocus();
            return;
        }

        if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
            Toast.makeText(this, R.string.err_invalid_location, Toast.LENGTH_SHORT).show();
            return;
        }

        // Save image to internal storage
        if (capturedBitmap != null) {
            savedImagePath = saveBitmapToFile(capturedBitmap);
        }

        long now = System.currentTimeMillis();
        String issueCategory = BACKEND_CATEGORIES[selectedPos];

        // Preserve the existing Room write during this first migration phase.
        Complaint c = new Complaint();
        c.issueType       = issueCategory;
        c.description     = description;
        c.status          = "Pending";
        c.latitude        = latitude;
        c.longitude       = longitude;
        c.ward            = ward;
        c.citizenEmail    = pref.getCitizenEmail();
        c.citizenName     = pref.getCitizenName();
        c.beforeImagePath = savedImagePath;
        c.createdAt       = now;
        c.timelineJson    = TimelineHelper.createInitial(now);

        long newId = AppDatabase.getInstance(this).complaintDao().insertComplaint(c);
        c.id = (int) newId;

        // Run risk analysis in background
        new Thread(() -> RiskAnalyzer.analyze(this, c)).start();

        // Notify admin
        NotificationHelper.showNewComplaintNotification(this, c.issueType, ward);

        beginRemoteSubmission(c, issueCategory, description, now);
    }

    /** Sends exactly one backend request after the existing local Room insert. */
    private void beginRemoteSubmission(Complaint complaint, String issueCategory,
                                       String description, long createdAt) {
        File imageFile = savedImagePath.isEmpty() ? null : new File(savedImagePath);
        ReportSubmission submission = new ReportSubmission(
                issueCategory,
                description,
                latitude,
                longitude,
                formatReportedAt(createdAt),
                "medium", // The existing UI has no severity selector yet.
                imageFile
        );

        setSubmissionInProgress(true);
        reportRepository.submitReport(submission, new ReportRepository.SubmitCallback() {
            @Override
            public void onSuccess(RemoteReportResponse response) {
                final String remoteId = (response != null && response.id != null)
                        ? response.id : null;
                if (remoteId != null) {
                    // Room writes must run off the main thread.
                    new Thread(() -> {
                        AppDatabase.getInstance(ReportIssueActivity.this)
                                .complaintDao().updateRemoteReportId(complaint.id, remoteId);
                    }).start();
                    complaint.remoteReportId = remoteId;
                }
                completeSubmission(getString(R.string.msg_report_success));
            }

            @Override
            public void onHttpError(int statusCode) {
                completeSubmission(getString(R.string.msg_report_saved_locally));
            }

            @Override
            public void onConnectionFailure(Throwable throwable) {
                completeSubmission(getString(R.string.msg_report_saved_locally));
            }

            @Override
            public void onConfigurationError(String message) {
                completeSubmission(getString(R.string.msg_report_saved_locally));
            }
        });
    }

    private String formatReportedAt(long timestampMs) {
        return OffsetDateTime.ofInstant(
                Instant.ofEpochMilli(timestampMs), ZoneId.systemDefault())
                .format(DateTimeFormatter.ISO_OFFSET_DATE_TIME);
    }

    private void setSubmissionInProgress(boolean inProgress) {
        isSubmitting = inProgress;
        btnSubmit.setEnabled(!inProgress);
        btnCapture.setEnabled(!inProgress);
        btnSubmit.setText(inProgress ? getString(R.string.msg_submitting) : submitButtonText);
    }

    private void completeSubmission(String message) {
        runOnUiThread(() -> {
            if (isFinishing()) return;
            setSubmissionInProgress(false);
            Toast.makeText(this, message, Toast.LENGTH_LONG).show();
            finish();
        });
    }

    private String saveBitmapToFile(Bitmap bitmap) {
        try {
            File dir = getExternalFilesDir(Environment.DIRECTORY_PICTURES);
            if (dir == null) dir = getFilesDir();
            File file = new File(dir, "complaint_" + System.currentTimeMillis() + ".jpg");
            FileOutputStream out = new FileOutputStream(file);
            bitmap.compress(Bitmap.CompressFormat.JPEG, 80, out);
            out.close();
            return file.getAbsolutePath();
        } catch (IOException e) {
            return "";
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode,
                                           String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQ_CAMERA && grantResults.length > 0
                && grantResults[0] == PackageManager.PERMISSION_GRANTED) openCamera();
        if (requestCode == REQ_LOCATION && grantResults.length > 0
                && grantResults[0] == PackageManager.PERMISSION_GRANTED) fetchLocation();
    }
}
