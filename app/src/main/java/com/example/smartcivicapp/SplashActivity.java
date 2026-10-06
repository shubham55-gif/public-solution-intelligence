package com.example.smartcivicapp;

import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.animation.AlphaAnimation;
import android.view.animation.Animation;
import android.view.animation.AnimationSet;
import android.view.animation.ScaleAnimation;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

/**
 * SplashActivity — animated splash screen.
 * Logo fades + scales in over 1s, then routes to the correct screen.
 */
public class SplashActivity extends AppCompatActivity {

    private static final int SPLASH_DELAY_MS = 2200;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        com.example.smartcivicapp.network.RetrofitClient.init(this);
        setContentView(R.layout.activity_splash);

        // Animate the content container
        LinearLayout container = findViewById(R.id.splashContainer);
        TextView tvVersion     = findViewById(R.id.tvVersion);

        // Scale + fade animation
        ScaleAnimation scale = new ScaleAnimation(
                0.7f, 1f, 0.7f, 1f,
                Animation.RELATIVE_TO_SELF, 0.5f,
                Animation.RELATIVE_TO_SELF, 0.5f);
        scale.setDuration(800);

        AlphaAnimation fade = new AlphaAnimation(0f, 1f);
        fade.setDuration(800);

        AnimationSet set = new AnimationSet(true);
        set.addAnimation(scale);
        set.addAnimation(fade);
        set.setFillAfter(true);

        if (container != null) container.startAnimation(set);

        // Fade in version text after main animation
        if (tvVersion != null) {
            AlphaAnimation vFade = new AlphaAnimation(0f, 1f);
            vFade.setDuration(600);
            vFade.setStartOffset(900);
            vFade.setFillAfter(true);
            tvVersion.startAnimation(vFade);
        }

        PrefManager pref = new PrefManager(this);

        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            Intent intent;
            if (pref.isAdminLoggedIn()) {
                intent = new Intent(this, AdminHomeActivity.class);
            } else if (pref.isCitizenLoggedIn()) {
                intent = new Intent(this, CitizenHomeActivity.class);
            } else {
                intent = new Intent(this, RoleSelectionActivity.class);
            }
            startActivity(intent);
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out);
            finish();
        }, SPLASH_DELAY_MS);
    }
}
