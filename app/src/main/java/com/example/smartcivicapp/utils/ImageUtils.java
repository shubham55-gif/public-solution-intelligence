package com.example.smartcivicapp.utils;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.View;
import android.widget.ImageView;

import androidx.annotation.Nullable;

import com.example.smartcivicapp.BuildConfig;
import com.example.smartcivicapp.R;

import java.io.File;
import java.io.InputStream;
import java.net.URL;

/**
 * ImageUtils — Universal helper for remote & local image URL construction and loading.
 * Ensures consistent handling for citizen before/after and admin before/after evidence photos.
 */
public final class ImageUtils {

    private static final String TAG = "ImageUtils";
    private static final Handler MAIN_HANDLER = new Handler(Looper.getMainLooper());

    private ImageUtils() {}

    /**
     * Builds a complete, normalized remote HTTP URL from a backend-relative or absolute path.
     * Rules:
     * - If path is null or empty, returns null.
     * - If path starts with http:// or https://, returns it directly.
     * - If path is relative (e.g. "uploads/reports/abc.jpg" or "/uploads/reports/abc.jpg"):
     *   prepends BuildConfig.BACKEND_BASE_URL and normalizes slashes cleanly.
     */
    public static String buildRemoteImageUrl(@Nullable String path) {
        if (path == null) return null;
        String trimmed = path.trim();
        if (trimmed.isEmpty()) return null;

        if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
            return trimmed;
        }

        String baseUrl = BuildConfig.BACKEND_BASE_URL;
        if (baseUrl == null || baseUrl.trim().isEmpty()) {
            return trimmed;
        }
        baseUrl = baseUrl.trim();
        while (baseUrl.endsWith("/")) {
            baseUrl = baseUrl.substring(0, baseUrl.length() - 1);
        }

        String cleanPath = trimmed;
        while (cleanPath.startsWith("/")) {
            cleanPath = cleanPath.substring(1);
        }

        return baseUrl + "/" + cleanPath;
    }

    /**
     * Asynchronously loads an image from a local file path or remote HTTP URL into an ImageView.
     * Manages fallback placeholder and optional 'unavailable' message view.
     */
    public static void loadEvidenceImage(
            @Nullable String path,
            @Nullable ImageView imageView,
            @Nullable View unavailableView
    ) {
        if (imageView == null) return;

        if (path == null || path.trim().isEmpty()) {
            imageView.setImageResource(R.drawable.bg_image_placeholder);
            if (unavailableView != null) unavailableView.setVisibility(View.VISIBLE);
            return;
        }

        String trimmed = path.trim();

        // 1. Check if local file exists
        if (trimmed.startsWith("/") || trimmed.startsWith("file:")) {
            String localPath = trimmed.startsWith("file://") ? trimmed.substring(7) : trimmed;
            File file = new File(localPath);
            if (file.exists() && file.isFile() && file.length() > 0) {
                Bitmap bmp = BitmapFactory.decodeFile(file.getAbsolutePath());
                if (bmp != null) {
                    imageView.setImageBitmap(bmp);
                    if (unavailableView != null) unavailableView.setVisibility(View.GONE);
                    return;
                }
            }
        }

        // 2. Load from Remote Backend URL
        String fullUrl = buildRemoteImageUrl(trimmed);
        if (fullUrl == null) {
            imageView.setImageResource(R.drawable.bg_image_placeholder);
            if (unavailableView != null) unavailableView.setVisibility(View.VISIBLE);
            return;
        }

        new Thread(() -> {
            try {
                InputStream is = new URL(fullUrl).openStream();
                Bitmap bmp = BitmapFactory.decodeStream(is);
                MAIN_HANDLER.post(() -> {
                    if (bmp != null) {
                        imageView.setImageBitmap(bmp);
                        if (unavailableView != null) unavailableView.setVisibility(View.GONE);
                    } else {
                        imageView.setImageResource(R.drawable.bg_image_placeholder);
                        if (unavailableView != null) unavailableView.setVisibility(View.VISIBLE);
                    }
                });
            } catch (Exception e) {
                Log.w(TAG, "Failed to load image from " + fullUrl + ": " + e.getMessage());
                MAIN_HANDLER.post(() -> {
                    imageView.setImageResource(R.drawable.bg_image_placeholder);
                    if (unavailableView != null) unavailableView.setVisibility(View.VISIBLE);
                });
            }
        }).start();
    }
}
