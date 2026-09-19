package com.soulsync.app.proactive

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat

object NotificationHelper {
    private const val CHANNEL_ID = "proactive_care"

    fun ensureChannel(context: android.content.Context) {
        val mgr = context.getSystemService(android.content.Context.NOTIFICATION_SERVICE)
                as NotificationManager
        val channel = NotificationChannel(
            CHANNEL_ID, "SoulSync", NotificationManager.IMPORTANCE_DEFAULT)
        channel.description = "Proactive care messages"
        mgr.createNotificationChannel(channel)
    }

    fun show(context: android.content.Context, message: String) {
        if (Build.VERSION.SDK_INT >= 33 &&
            context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED) {
            return // 未授权则静默丢弃（V2 加 in-app 通知）
        }
        ensureChannel(context)
        val notif = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("SoulSync")
            .setContentText(message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .setAutoCancel(true)
            .build()
        NotificationManagerCompat.from(context).notify(1001, notif)
    }
}
