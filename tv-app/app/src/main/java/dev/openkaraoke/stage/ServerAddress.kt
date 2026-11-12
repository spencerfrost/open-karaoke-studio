package dev.openkaraoke.stage

import android.content.Context
import androidx.core.content.edit
import androidx.core.net.toUri

/** The server the stage loads from: prod unless an override (for the dev server) is saved. */
object ServerAddress {
    const val DEFAULT = "https://karaoke.mrspinn.ca"

    private const val PREFS = "server"
    private const val KEY_ADDRESS = "address"

    fun get(context: Context): String =
        prefs(context).getString(KEY_ADDRESS, null) ?: DEFAULT

    fun set(context: Context, address: String) {
        prefs(context).edit { putString(KEY_ADDRESS, address) }
    }

    fun reset(context: Context) {
        prefs(context).edit { remove(KEY_ADDRESS) }
    }

    fun stageUrl(address: String): String = "$address/stage"

    /**
     * Turns what was typed into an origin like `http://192.168.1.20:5193`, or null if it isn't
     * one. A missing scheme means http, since only the dev server is ever typed in.
     */
    fun normalize(input: String): String? {
        val trimmed = input.trim().trimEnd('/')
        if (trimmed.isEmpty()) return null
        val withScheme = if ("://" in trimmed) trimmed else "http://$trimmed"
        val uri = withScheme.toUri()
        if (uri.scheme !in setOf("http", "https") || uri.host.isNullOrEmpty()) return null
        val port = if (uri.port != -1) ":${uri.port}" else ""
        return "${uri.scheme}://${uri.host}$port"
    }

    /** `https://karaoke.mrspinn.ca` → `karaoke.mrspinn.ca`, for labels. */
    fun label(address: String): String = address.substringAfter("://")

    private fun prefs(context: Context) =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
}
