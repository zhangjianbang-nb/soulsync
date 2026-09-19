package com.soulsync.app

import android.app.Application
import android.app.job.JobInfo
import android.app.job.JobScheduler
import android.content.ComponentName
import android.content.Context
import com.soulsync.app.proactive.ProactiveWorker

/** 全局 Application：持有 API 客户端与用户 id，注册主动关怀轮询任务。 */
class SoulSyncApplication : Application() {

    var api: com.soulsync.app.SoulSyncApi? = null
    var userId: String? = null
        private set

    override fun onCreate() {
        super.onCreate()
        userId = android.provider.Settings.Secure.getString(
            contentResolver, android.provider.Settings.Secure.ANDROID_ID)?.take(8)
            ?.let { "user_$it" } ?: "user_default"
        scheduleProactivePoll()
    }

    /** 每 30 分钟唤醒一次主动关怀轮询（服务端负责节流，这里只是心跳）。 */
    private fun scheduleProactivePoll() {
        val scheduler = getSystemService(Context.JOB_SCHEDULER_SERVICE) as JobScheduler
        val job = JobInfo.Builder(
            1001, ComponentName(this, ProactiveWorker::class.java))
            .setPeriodic(30 * 60 * 1000L)
            .setPersisted(true)
            .build()
        scheduler.schedule(job)
    }
}
