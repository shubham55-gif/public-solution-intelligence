package com.example.smartcivicapp.utils;

import android.content.Context;
import android.content.res.Configuration;
import android.content.res.Resources;
import android.os.Build;
import android.os.LocaleList;

import com.example.smartcivicapp.PrefManager;

import java.util.Locale;

/**
 * LocaleHelper — manages dynamic locale switching and persistence for citizen multi-language support.
 */
public class LocaleHelper {

    public static final String LANGUAGE_ENGLISH = "en";
    public static final String LANGUAGE_MARATHI = "mr";
    public static final String LANGUAGE_HINDI   = "hi";

    public static Context onAttach(Context context) {
        if (context == null) return null;
        PrefManager pref = new PrefManager(context);
        String lang = pref.getLanguage();
        return setLocale(context, lang);
    }

    public static Context setLocale(Context context, String language) {
        if (context == null) return null;
        if (language == null || language.trim().isEmpty()) {
            language = LANGUAGE_ENGLISH;
        }

        Locale locale = new Locale(language);
        Locale.setDefault(locale);

        Resources resources = context.getResources();
        if (resources == null) return context;
        Configuration configuration = new Configuration(resources.getConfiguration());

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            configuration.setLocale(locale);
            LocaleList localeList = new LocaleList(locale);
            LocaleList.setDefault(localeList);
            configuration.setLocales(localeList);
            return context.createConfigurationContext(configuration);
        } else {
            configuration.locale = locale;
            resources.updateConfiguration(configuration, resources.getDisplayMetrics());
            return context;
        }
    }

    public static void applyLocale(Context context) {
        if (context == null) return;
        PrefManager pref = new PrefManager(context);
        String language = pref.getLanguage();
        if (language == null || language.trim().isEmpty()) {
            language = LANGUAGE_ENGLISH;
        }

        Locale locale = new Locale(language);
        Locale.setDefault(locale);

        Resources resources = context.getResources();
        if (resources != null) {
            Configuration configuration = resources.getConfiguration();
            if (configuration != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                    configuration.setLocale(locale);
                    LocaleList localeList = new LocaleList(locale);
                    LocaleList.setDefault(localeList);
                    configuration.setLocales(localeList);
                } else {
                    configuration.locale = locale;
                }
                resources.updateConfiguration(configuration, resources.getDisplayMetrics());
            }
        }
    }
}
