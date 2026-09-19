package com.soulsync.app.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.soulsync.app.AppSession
import com.soulsync.app.R
import com.soulsync.app.net.SoulSyncApi
import kotlinx.coroutines.launch

/**
 * SoulSync 主界面：连接页 + 聊天 + 记忆面板 + 设置。
 * 多语言 UI 由 Android 资源系统按系统语言自动切换（values/-en/-ja/-ko）。
 */
@Composable
fun SoulSyncApp(session: AppSession) {
    var tab by remember { mutableIntStateOf(0) }
    MaterialTheme(colorScheme = darkColorScheme()) {
        Scaffold(bottomBar = {
            NavigationBar {
                listOf(R.string.chat_hint to "💬", R.string.memories to "🧠", R.string.settings to "⚙️")
                    .forEachIndexed { i, (label, icon) ->
                        NavigationBarItem(
                            selected = tab == i,
                            onClick = { tab = i },
                            icon = { Text(icon, style = MaterialTheme.typography.titleLarge) },
                            label = { Text(stringResource(label)) },
                        )
                    }
            }
        }) { pad ->
            Box(Modifier.padding(pad)) {
                when (tab) {
                    0 -> ChatPage(session)
                    1 -> MemoriesPage(session)
                    else -> SettingsPage(session)
                }
            }
        }
    }
}

// ---------- 聊天 ----------

data class Bubble(val fromMe: Boolean, val text: String, val meta: String? = null)

@Composable
fun ChatPage(session: AppSession) {
    val scope = rememberCoroutineScope()
    val bubbles = remember { mutableStateListOf<Bubble>() }
    var input by remember { mutableStateOf("") }
    var sending by remember { mutableStateOf(false) }
    var identityName by remember { mutableStateOf<String?>(null) }
    var emotion by remember { mutableStateOf<String?>(null) }
    val api = session.api

    Column(Modifier.fillMaxSize().padding(12.dp)) {
        // 顶部状态条：身份 + 情绪
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(identityName?.let { "${stringResource(R.string.known_as)}: $it" }
                 ?: stringResource(R.string.not_connected),
                 style = MaterialTheme.typography.labelLarge)
            emotion?.let { Text("${stringResource(R.string.emotion_state)}: $it",
                                style = MaterialTheme.typography.labelLarge) }
        }
        LazyColumn(Modifier.weight(1f).fillMaxWidth(), reverseLayout = false) {
            items(bubbles) { b ->
                ChatBubble(b)
                Spacer(Modifier.height(6.dp))
            }
        }
        Row(verticalAlignment = Alignment.Bottom) {
            OutlinedTextField(
                value = input, onValueChange = { input = it },
                modifier = Modifier.weight(1f),
                placeholder = { Text(stringResource(R.string.chat_hint)) },
                maxLines = 4,
            )
            Spacer(Modifier.width(8.dp))
            Button(onClick = {
                val text = input.trim()
                if (text.isEmpty() || sending || api == null) return@Button
                input = ""
                sending = true
                bubbles.add(Bubble(true, text))
                scope.launch {
                    try {
                        val r = api.chat(session.userId.value, text)
                        bubbles.add(Bubble(false, r.reply,
                            meta = "${r.emotionLabel}(${r.emotionValence})"))
                        identityName = r.identityName ?: identityName
                        emotion = r.emotionLabel
                    } catch (e: Exception) {
                        bubbles.add(Bubble(false, "⚠ ${e.message}"))
                    } finally { sending = false }
                }
            }, enabled = !sending && api != null) {
                Text(if (sending) "…" else stringResource(R.string.send))
            }
        }
        TextButton(onClick = {
            scope.launch {
                runCatching { api?.sessionEnd(session.userId.value) }
            }
        }) { Text(stringResource(R.string.session_end), style = MaterialTheme.typography.labelSmall) }
    }
}

@Composable
fun ChatBubble(b: Bubble) {
    Row(Modifier.fillMaxWidth(),
        horizontalArrangement = if (b.fromMe) Arrangement.End else Arrangement.Start) {
        Surface(
            shape = RoundedCornerShape(16.dp),
            color = if (b.fromMe) MaterialTheme.colorScheme.primary
                    else MaterialTheme.colorScheme.surfaceVariant,
        ) {
            Column(Modifier.padding(10.dp)) {
                Text(b.text, color = if (b.fromMe) MaterialTheme.colorScheme.onPrimary
                        else MaterialTheme.colorScheme.onSurface)
                b.meta?.let {
                    Text(it, style = MaterialTheme.typography.labelSmall,
                         color = MaterialTheme.colorScheme.outline)
                }
            }
        }
    }
}

// ---------- 记忆 ----------

@Composable
fun MemoriesPage(session: AppSession) {
    val scope = rememberCoroutineScope()
    val items = remember { mutableStateListOf<SoulSyncApi.MemoryItem>() }
    LaunchedEffect(session.api) {
        session.api?.let { api ->
            runCatching { items.addAll(api.memories(session.userId.value)) }
        }
    }
    Column(Modifier.fillMaxSize().padding(12.dp)) {
        Text(stringResource(R.string.memories), style = MaterialTheme.typography.titleLarge)
        Spacer(Modifier.height(8.dp))
        if (items.isEmpty()) {
            Text(stringResource(R.string.memory_empty),
                 color = MaterialTheme.colorScheme.outline)
        }
        LazyColumn {
            items(items) { m ->
                ListItem(
                    headlineContent = { Text(m.content) },
                    supportingContent = {
                        Text("${m.layer} · ${m.emotion ?: "-"} · ${"%.2f".format(m.importance)}")
                    },
                    trailingContent = {
                        TextButton(onClick = {
                            scope.launch { runCatching {
                                    session.api?.deleteMemory(m.id)
                            } }
                        }) { Text("✕") }
                    },
                )
            }
        }
    }
}

// ---------- 设置 ----------

@Composable
fun SettingsPage(session: AppSession) {
    var url by remember { mutableStateOf(session.serverUrl) }
    var status by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(stringResource(R.string.settings), style = MaterialTheme.typography.titleLarge)
        OutlinedTextField(value = url, onValueChange = { url = it },
                          label = { Text(stringResource(R.string.server_url)) },
                          modifier = Modifier.fillMaxWidth())
        Row {
            Button(onClick = {
                val ok = session.connect(url)
                status = if (ok) "✓" else "✗"
                scope.launch { session.api?.let { a ->
                    status = if (runCatching { a.health() }.getOrDefault(false)) "✓ connected"
                             else "✗ unreachable"
                } }
            }) { Text(stringResource(R.string.connect)) }
            Spacer(Modifier.width(12.dp))
            status?.let { Text(it, modifier = Modifier.align(Alignment.CenterVertically)) }
        }
        HorizontalDivider()
        Text(stringResource(R.string.proactive_care),
             style = MaterialTheme.typography.titleMedium)
        Text("服务端每轮评估「内心独白」分数，超过阈值主动问候；连续负面回应自动降频。",
             style = MaterialTheme.typography.bodySmall,
             color = MaterialTheme.colorScheme.outline)
        TextButton(onClick = {
            scope.launch { runCatching { session.api?.forgetMe(session.userId.value) } }
        }) { Text(stringResource(R.string.forget_me),
                  color = MaterialTheme.colorScheme.error) }
    }
}
