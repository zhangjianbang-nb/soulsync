package com.soulsync.app.net

import android.util.Base64
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.suspendCancellableCoroutine
import okhttp3.Call
import okhttp3.Callback
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/** 服务端 API 客户端（OkHttp，JSON）。 */
class SoulSyncApi(private var baseUrl: String) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .build()

    private val json = "application/json; charset=utf-8".toMediaType()

    data class ChatResult(
        val reply: String,
        val turnId: String,
        val identityName: String?,
        val identityConfirmed: Boolean,
        val emotionLabel: String,
        val emotionValence: Double,
        val memoriesUsed: List<String>,
        val crisis: Boolean,
    )

    data class MemoryItem(
        val id: String, val layer: String, val content: String,
        val importance: Double, val emotion: String?, val createdAt: Double,
    )

    suspend fun chat(
        userId: String, text: String,
        faceJpeg: ByteArray? = null,
        voicePcm16k: ByteArray? = null,
    ): ChatResult = withContext(Dispatchers.IO) {
        val body = JSONObject().apply {
            put("user_id", userId)
            put("text", text)
            faceJpeg?.let { put("face_b64", Base64.encodeToString(it, Base64.NO_WRAP)) }
            voicePcm16k?.let {
                put("voice_wav_b64", Base64.encodeToString(floatBytes(it), Base64.NO_WRAP))
            }
        }
        val resp = post("/v1/chat", body)
        val j = JSONObject(resp)
        val identity = j.getJSONObject("identity")
        val emotion = j.getJSONObject("emotion")
        val memories = j.getJSONArray("memories_used").let { arr ->
            (0 until arr.length()).map { arr.getString(it) }
        }
        ChatResult(
            reply = j.getString("reply"),
            turnId = j.getString("turn_id"),
            identityName = if (identity.isNull("name")) null else identity.getString("name"),
            identityConfirmed = identity.getBoolean("confirmed"),
            emotionLabel = emotion.getString("label"),
            emotionValence = emotion.getDouble("valence"),
            memoriesUsed = memories,
            crisis = j.getBoolean("crisis"),
        )
    }

    suspend fun proactive(userId: String): String? = withContext(Dispatchers.IO) {
        val resp = post("/v1/proactive", JSONObject().put("user_id", userId))
        val j = JSONObject(resp)
        if (j.isNull("message")) null else j.getString("message")
    }

    suspend fun proactiveReaction(userId: String, reaction: String) =
        withContext(Dispatchers.IO) {
            post("/v1/proactive/reaction", JSONObject()
                .put("user_id", userId).put("reaction", reaction))
        }

    suspend fun sessionEnd(userId: String) = withContext(Dispatchers.IO) {
        post("/v1/session/end", JSONObject().put("user_id", userId))
    }

    suspend fun memories(userId: String, limit: Int = 50): List<MemoryItem> =
        withContext(Dispatchers.IO) {
            val resp = get("/v1/memories/$userId?limit=$limit")
            val arr = JSONArray(resp)
            (0 until arr.length()).map { i ->
                val m = arr.getJSONObject(i)
                MemoryItem(
                    id = m.getString("id"), layer = m.getString("layer"),
                    content = m.getString("content"), importance = m.getDouble("importance"),
                    emotion = if (m.isNull("emotion")) null else m.getString("emotion"),
                    createdAt = m.getDouble("created_at"),
                )
            }
        }

    suspend fun deleteMemory(memoryId: String) = withContext(Dispatchers.IO) {
        delete("/v1/memories/x/" + memoryId)
    }

    suspend fun forgetMe(userId: String) = withContext(Dispatchers.IO) {
        delete("/v1/user/" + userId)
    }

    suspend fun setName(userId: String, identityId: String, name: String) =
        withContext(Dispatchers.IO) {
            post("/v1/identity/name", JSONObject()
                .put("user_id", userId).put("identity_id", identityId).put("name", name))
        }

    suspend fun health(): Boolean = withContext(Dispatchers.IO) {
        runCatching { get("/v1/health") }.isSuccess
    }

    // ---------- HTTP 基元 ----------

    private suspend fun post(path: String, body: JSONObject): String =
        request(Request.Builder()
            .url("$baseUrl$path")
            .post(body.toString().toRequestBody(json))
            .build())

    private suspend fun get(path: String): String =
        request(Request.Builder().url("$baseUrl$path").build())

    private suspend fun delete(path: String): String =
        request(Request.Builder().url("$baseUrl$path").delete().build())

    private suspend fun request(req: Request): String = suspendCancellableCoroutine { cont ->
        client.newCall(req).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                if (cont.isActive) cont.resumeWith(Result.failure(e))
            }
            override fun onResponse(call: Call, response: Response) {
                response.use {
                    val text = it.body?.string().orEmpty()
                    if (it.isSuccessful) {
                        if (cont.isActive) cont.resumeWith(Result.success(text))
                    } else {
                        if (cont.isActive) cont.resumeWith(Result.failure(
                            IOException("HTTP ${it.code}: ${text.take(200)}")))
                    }
                }
            }
        })
    }

    /** 16bit PCM → 32bit float bytes（服务端 voice_wav_b64 期望 float32）。 */
    private fun floatBytes(pcm16: ByteArray): ByteArray {
        val n = pcm16.size / 2
        val out = ByteArray(n * 4)
        for (i in 0 until n) {
            val lo = pcm16[i * 2].toInt() and 0xFF
            val hi = pcm16[i * 2 + 1].toInt()
            val sample = ((hi shl 8) or lo).toShort().toFloat() / 32768f
            val bits = java.lang.Float.floatToIntBits(sample)
            out[i * 4] = (bits shr 0).toByte()
            out[i * 4 + 1] = (bits shr 8).toByte()
            out[i * 4 + 2] = (bits shr 16).toByte()
            out[i * 4 + 3] = (bits shr 24).toByte()
        }
        return out
    }
}
