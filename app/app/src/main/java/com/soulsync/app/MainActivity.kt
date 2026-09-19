package com.soulsync.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewmodel.compose.viewModel
import com.soulsync.app.net.SoulSyncApi
import com.soulsync.app.ui.SoulSyncApp
import kotlinx.coroutines.flow.MutableStateFlow

/** 全局会话状态：服务器地址 / 用户 id / API 客户端。 */
class AppSession : ViewModel() {
    var serverUrl by mutableStateOf("http://192.168.1.100:8800")
    val userId = MutableStateFlow("user_local")

    var api: SoulSyncApi? = null
        private set

    fun connect(url: String): Boolean {
        val normalized = url.trim().trimEnd('/')
        return runCatching {
            SoulSyncApi(normalized)
        }.onSuccess { api = it; serverUrl = normalized }.isSuccess
    }
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val session: AppSession = viewModel()
            SoulSyncApp(session)
        }
    }
}
