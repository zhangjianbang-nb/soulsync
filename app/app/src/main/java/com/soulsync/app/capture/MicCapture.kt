package com.soulsync.app.capture

import android.annotation.SuppressLint
import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder

/** 麦克风采集：16kHz 单声道 PCM16，供声纹/语音情绪上传。 */
object MicCapture {

    private const val SAMPLE_RATE = 16000

    @SuppressLint("MissingPermission")
    fun recordPcm(context: Context, seconds: Float): ByteArray? {
        val minBuf = AudioRecord.getMinBufferSize(
            SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        if (minBuf <= 0) return null
        val record = AudioRecord(
            MediaRecorder.AudioSource.MIC, SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, minBuf * 4)
        return try {
            record.startRecording()
            val totalSamples = (SAMPLE_RATE * seconds).toInt()
            val out = ByteArray(totalSamples * 2)
            var offset = 0
            while (offset < out.size) {
                val n = record.read(out, offset, out.size - offset)
                if (n <= 0) break
                offset += n
            }
            out.copyOf(offset)
        } finally {
            record.stop()
            record.release()
        }
    }
}
