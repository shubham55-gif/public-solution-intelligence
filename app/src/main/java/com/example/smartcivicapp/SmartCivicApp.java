package com.example.smartcivicapp;

import android.app.Application;
import com.example.smartcivicapp.network.RetrofitClient;

public class SmartCivicApp extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
        RetrofitClient.init(this);
    }
}
