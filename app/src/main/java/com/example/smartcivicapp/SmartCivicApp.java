package com.example.smartcivicapp;

import android.app.Application;
import android.content.Context;

import com.example.smartcivicapp.network.RetrofitClient;

public class SmartCivicApp extends Application {

    @Override
    protected void attachBaseContext(Context base) {
        super.attachBaseContext(base);
    }

    @Override
    public void onCreate() {
        super.onCreate();
        RetrofitClient.init(this);
    }
}
