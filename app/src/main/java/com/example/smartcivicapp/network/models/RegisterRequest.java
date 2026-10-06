package com.example.smartcivicapp.network.models;

import com.google.gson.annotations.SerializedName;

public class RegisterRequest {
    @SerializedName("name")
    public final String name;

    @SerializedName("email")
    public final String email;

    @SerializedName("phone")
    public final String phone;

    @SerializedName("password")
    public final String password;

    public RegisterRequest(String name, String email, String phone, String password) {
        this.name = name;
        this.email = email;
        this.phone = phone;
        this.password = password;
    }
}
