package com.example.smartcivicapp;

import android.os.Bundle;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Spinner;

import androidx.appcompat.app.AppCompatActivity;

import com.example.smartcivicapp.database.AppDatabase;
import com.example.smartcivicapp.entities.Complaint;
import com.example.smartcivicapp.repositories.ReportRepository;
import com.google.android.gms.maps.CameraUpdateFactory;
import com.google.android.gms.maps.GoogleMap;
import com.google.android.gms.maps.OnMapReadyCallback;
import com.google.android.gms.maps.SupportMapFragment;
import com.google.android.gms.maps.model.BitmapDescriptorFactory;
import com.google.android.gms.maps.model.LatLng;
import com.google.android.gms.maps.model.MarkerOptions;

import java.util.List;

/**
 * MapsActivity — Google Maps with filter + info windows.
 *
 * NEW FEATURES:
 *  - Filter by status spinner
 *  - Filter by issue type spinner
 *  - Custom info window: shows issue type, status, area, time ago
 *  - Color-coded markers (Red=Pending, Yellow=In Progress, Green=Resolved)
 *  - High-risk markers are larger (represented by a different hue)
 *  - Single-complaint mode (from detail screen)
 */
public class MapsActivity extends AppCompatActivity implements OnMapReadyCallback {

    private static final LatLng DEFAULT_INDIA = new LatLng(20.5937, 78.9629);

    private GoogleMap mMap;
    private Spinner   spinnerStatus, spinnerType;

    private String filterStatus = "All";
    private String filterType   = "All";
    private PrefManager pref;
    private ReportRepository reportRepository;
    private List<Complaint> remoteComplaints;
    private boolean remoteLoadInProgress;
    private boolean remoteLoadFinished;
    private boolean remoteLoadFailed;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_maps);

        spinnerStatus = findViewById(R.id.spinnerMapStatus);
        spinnerType   = findViewById(R.id.spinnerMapType);
        pref = new PrefManager(this);
        reportRepository = new ReportRepository(this);

        // Check for single-complaint mode (no filters shown)
        boolean singleMode = getIntent().hasExtra("LAT");
        if (singleMode) {
            if (spinnerStatus != null) spinnerStatus.setVisibility(View.GONE);
            if (spinnerType   != null) spinnerType.setVisibility(View.GONE);
        }

        if (spinnerStatus != null && !singleMode) {
            setupFilters();
        }

        SupportMapFragment mapFrag = (SupportMapFragment)
                getSupportFragmentManager().findFragmentById(R.id.map);
        if (mapFrag != null) mapFrag.getMapAsync(this);
    }

    private void setupFilters() {
        String[] statuses = {"All", "Pending", "In Progress", "Resolved"};
        spinnerStatus.setAdapter(new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_item, statuses));
        spinnerStatus.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> p, View v, int pos, long id) {
                filterStatus = statuses[pos]; refreshMarkers();
            }
            @Override public void onNothingSelected(AdapterView<?> p) {}
        });

        String[] types = {"All", "Road Damage", "Garbage Overflow",
                "Water Leakage", "Street Light Issue"};
        spinnerType.setAdapter(new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_item, types));
        spinnerType.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> p, View v, int pos, long id) {
                filterType = types[pos]; refreshMarkers();
            }
            @Override public void onNothingSelected(AdapterView<?> p) {}
        });
    }

    @Override
    public void onMapReady(GoogleMap googleMap) {
        mMap = googleMap;
        mMap.getUiSettings().setZoomControlsEnabled(true);
        mMap.getUiSettings().setMapToolbarEnabled(true);

        // Single-complaint mode
        double lat   = getIntent().getDoubleExtra("LAT", -999);
        double lng   = getIntent().getDoubleExtra("LNG", -999);
        String title = getIntent().getStringExtra("TITLE");

        if (lat != -999 && lng != -999) {
            if (isValidCoordinate(lat, lng)) {
                LatLng pos = new LatLng(lat, lng);
                mMap.addMarker(new MarkerOptions()
                        .position(pos)
                        .title(title != null ? title : "Complaint")
                        .icon(BitmapDescriptorFactory.defaultMarker(
                                BitmapDescriptorFactory.HUE_AZURE)));
                mMap.moveCamera(CameraUpdateFactory.newLatLngZoom(pos, 16f));
            } else {
                mMap.moveCamera(CameraUpdateFactory.newLatLngZoom(DEFAULT_INDIA, 4f));
            }
        } else if (pref.isCitizen()) {
            loadRemoteComplaints();
        } else {
            refreshMarkers();
        }
    }

    private void refreshMarkers() {
        if (mMap == null) return;
        mMap.clear();

        List<Complaint> all;
        if (pref.isCitizen() && !remoteLoadFailed) {
            if (!remoteLoadFinished) return;
            all = remoteComplaints;
        } else {
            all = AppDatabase.getInstance(this)
                    .complaintDao().getAllComplaints();
        }

        if (all == null || all.isEmpty()) {
            mMap.moveCamera(CameraUpdateFactory.newLatLngZoom(DEFAULT_INDIA, 4f));
            return;
        }

        LatLng firstValid = null;

        for (int i = 0; i < all.size(); i++) {
            Complaint c = all.get(i);
            if (!isValidCoordinate(c.latitude, c.longitude)) continue;

            // Apply filters
            if (!"All".equals(filterStatus) && !filterStatus.equalsIgnoreCase(c.status)) continue;
            if (!"All".equals(filterType)   && !filterType.equalsIgnoreCase(c.issueType)) continue;

            LatLng pos = new LatLng(
                    c.latitude  + (i * 0.00005),
                    c.longitude + (i * 0.00005));

            // Color by status
            float hue;
            if ("Resolved".equalsIgnoreCase(c.status))   hue = BitmapDescriptorFactory.HUE_GREEN;
            else if ("In Progress".equalsIgnoreCase(c.status)) hue = BitmapDescriptorFactory.HUE_YELLOW;
            else hue = BitmapDescriptorFactory.HUE_RED;

            // High-risk gets orange
            if ("High".equalsIgnoreCase(c.riskLevel)) hue = BitmapDescriptorFactory.HUE_ORANGE;

            String snippet = "Status: " + c.status +
                    (c.ward != null && !c.ward.isEmpty() ? " | Area: " + c.ward : "") +
                    (c.isRepeat ? " | ⚠ REPEAT" : "");

            mMap.addMarker(new MarkerOptions()
                    .position(pos)
                    .title(c.issueType)
                    .snippet(snippet)
                    .icon(BitmapDescriptorFactory.defaultMarker(hue)));

            if (firstValid == null) firstValid = new LatLng(c.latitude, c.longitude);
        }

        if (firstValid != null) {
            mMap.moveCamera(CameraUpdateFactory.newLatLngZoom(firstValid, 13f));
        } else {
            mMap.moveCamera(CameraUpdateFactory.newLatLngZoom(DEFAULT_INDIA, 4f));
        }
    }

    private void loadRemoteComplaints() {
        if (remoteLoadInProgress || remoteLoadFinished || !pref.isCitizen()) return;

        remoteLoadInProgress = true;
        android.widget.Toast.makeText(this, "Loading map reports...",
                android.widget.Toast.LENGTH_SHORT).show();
        reportRepository.getMyReports(new ReportRepository.ReportListCallback() {
            @Override
            public void onSuccess(List<Complaint> reports) {
                runOnUiThread(() -> {
                    remoteComplaints = reports;
                    remoteLoadInProgress = false;
                    remoteLoadFinished = true;
                    remoteLoadFailed = false;
                    refreshMarkers();
                });
            }

            @Override
            public void onHttpError(int statusCode) {
                showRemoteFallback("Could not load map reports (HTTP " + statusCode + ").");
            }

            @Override
            public void onFailure(Throwable throwable) {
                showRemoteFallback("Could not reach the server. Showing saved map reports.");
            }

            @Override
            public void onMalformedResponse(Throwable throwable) {
                showRemoteFallback("The server returned invalid map data. Showing saved reports.");
            }

            @Override
            public void onConfigurationError(String message) {
                showRemoteFallback("Server is not configured. Showing saved map reports.");
            }
        });
    }

    private void showRemoteFallback(String message) {
        runOnUiThread(() -> {
            remoteLoadInProgress = false;
            remoteLoadFinished = true;
            remoteLoadFailed = true;
            remoteComplaints = null;
            android.widget.Toast.makeText(this, message,
                    android.widget.Toast.LENGTH_LONG).show();
            refreshMarkers();
        });
    }

    private boolean isValidCoordinate(double latitude, double longitude) {
        return Double.isFinite(latitude) && Double.isFinite(longitude)
                && latitude >= -90 && latitude <= 90
                && longitude >= -180 && longitude <= 180
                && !(latitude == 0 && longitude == 0);
    }
}
