package com.soulsync.app.proactive

import android.app.job.JobParameters
import android.app.job.JobService
import kotlinx.coroutines.runBlocking

/**
 * 主动关怀轮询：系统 JobScheduler 定期唤醒，调 /v1/proactive。
 * 服务端做全部决策（内心独白门控/间隔/上限/降频），App 只负责送达与展示。
 */
class ProactiveWorker : JobService() {

    override fun onStartJob(params: JobParameters?): Boolean {
        val api = (application as? SoulSyncApplication)?.api ?: return false
        val userId = (application as? SoulSyncApplication)?.userId ?: return false
        runBlocking {
            runCatching { api.proactive(userId) }.onSuccess { msg ->
                if (msg != null) {
                    NotificationHelper.show(applicationContext, msg)
                }
            }
        }
        return false // 无后台工作剩余
    }

    override fun onStopJob(params: JobParameters?): Boolean = false
}
