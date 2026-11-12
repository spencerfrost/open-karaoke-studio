package dev.openkaraoke.stage

import android.annotation.SuppressLint
import android.content.Intent
import android.os.Bundle
import android.view.InputDevice
import android.view.KeyCharacterMap
import android.view.KeyEvent
import android.view.View
import android.view.WindowManager
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.core.view.isVisible

/**
 * The stage, full screen in a WebView, driven by the TV remote.
 *
 * Remote keys are translated into the keys the stage already listens for (Back → Escape,
 * play/pause → Space, D-pad center → Enter) as native key events, so the page sees trusted
 * keydowns with the right `e.code` and the first press counts as user activation for autoplay.
 * Long-pressing Back opens a small menu instead.
 */
class StageActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var errorPanel: View
    private lateinit var errorDetail: TextView

    private lateinit var server: String

    /** Set once a held Back has opened the menu, so its release isn't also sent as Escape. */
    private var backLongPressed = false

    private val serverAddressLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == RESULT_OK) loadStage()
        }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_stage)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        hideSystemBars()

        webView = findViewById(R.id.web_view)
        errorPanel = findViewById(R.id.error_panel)
        errorDetail = findViewById(R.id.error_detail)

        findViewById<Button>(R.id.error_retry).setOnClickListener { loadStage() }
        findViewById<Button>(R.id.error_change_server).setOnClickListener { openServerAddress() }

        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
        CookieManager.getInstance().setAcceptCookie(true)

        webView.settings.apply {
            javaScriptEnabled = true
            // The auth token and the host's session live in localStorage.
            domStorageEnabled = true
            @Suppress("DEPRECATION")
            databaseEnabled = true
            mediaPlaybackRequiresUserGesture = false
        }
        webView.webChromeClient = WebChromeClient()
        webView.webViewClient = StageWebViewClient()

        loadStage()
    }

    override fun onResume() {
        super.onResume()
        // No reload: the page reconnects its own WebSocket, and a reload would lose the night's
        // in-memory state.
        webView.onResume()
    }

    override fun onPause() {
        webView.onPause()
        CookieManager.getInstance().flush()
        super.onPause()
    }

    override fun onDestroy() {
        webView.destroy()
        super.onDestroy()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) hideSystemBars()
    }

    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        if (event.keyCode == KeyEvent.KEYCODE_BACK) {
            handleBack(event)
            return true
        }
        // The error screen uses the remote for its own buttons.
        if (errorPanel.isVisible) return super.dispatchKeyEvent(event)

        val translated = PAGE_KEYS[event.keyCode] ?: return super.dispatchKeyEvent(event)
        return webView.dispatchKeyEvent(pageKeyEvent(event, translated, event.action))
    }

    /**
     * Back never leaves the app. A short press goes to the page as Escape, sent on release
     * because only then is it known not to be a long press. A long press opens the menu.
     */
    private fun handleBack(event: KeyEvent) {
        when (event.action) {
            KeyEvent.ACTION_DOWN -> {
                if (event.repeatCount == 0) {
                    backLongPressed = false
                } else if (event.isLongPress && !backLongPressed) {
                    backLongPressed = true
                    showMenu()
                }
            }
            KeyEvent.ACTION_UP -> {
                if (backLongPressed || event.isCanceled || errorPanel.isVisible) return
                webView.dispatchKeyEvent(pageKeyEvent(event, ESCAPE, KeyEvent.ACTION_DOWN))
                webView.dispatchKeyEvent(pageKeyEvent(event, ESCAPE, KeyEvent.ACTION_UP))
            }
        }
    }

    private fun showMenu() {
        AlertDialog.Builder(this)
            .setTitle(ServerAddress.label(server))
            .setItems(
                arrayOf(
                    getString(R.string.menu_reload),
                    getString(R.string.menu_server_address),
                    getString(R.string.menu_exit),
                ),
            ) { _, which ->
                when (which) {
                    0 -> if (errorPanel.isVisible) loadStage() else webView.reload()
                    1 -> openServerAddress()
                    2 -> finish()
                }
            }
            .show()
    }

    private fun loadStage() {
        server = ServerAddress.get(this)
        errorPanel.isVisible = false
        webView.loadUrl(ServerAddress.stageUrl(server))
        webView.requestFocus()
    }

    private fun showError() {
        errorDetail.text = getString(R.string.error_detail, ServerAddress.label(server))
        errorPanel.isVisible = true
        findViewById<View>(R.id.error_retry).requestFocus()
    }

    private fun openServerAddress() {
        serverAddressLauncher.launch(Intent(this, ServerAddressActivity::class.java))
    }

    private fun hideSystemBars() {
        WindowCompat.getInsetsController(window, window.decorView).apply {
            systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            hide(WindowInsetsCompat.Type.systemBars())
        }
    }

    private inner class StageWebViewClient : WebViewClient() {
        /** In-app links stay in the WebView; anything off-origin is ignored. */
        override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean =
            ServerAddress.normalize(request.url.toString()) != server

        override fun onReceivedError(
            view: WebView,
            request: WebResourceRequest,
            error: WebResourceError,
        ) {
            if (request.isForMainFrame) showError()
        }

        /** A 502 from the proxy while the frontend container is down is also "can't reach". */
        override fun onReceivedHttpError(
            view: WebView,
            request: WebResourceRequest,
            errorResponse: WebResourceResponse,
        ) {
            if (request.isForMainFrame && errorResponse.statusCode >= 500) showError()
        }
    }

    /** A key the page knows: Android key code plus the Linux scan code Chromium reads `e.code` from. */
    private data class PageKey(val keyCode: Int, val scanCode: Int)

    /**
     * Builds the event the page receives. It comes from the virtual keyboard so `e.key` resolves
     * through a full key map (a remote's map may not know Space), and keeps the original timing
     * and repeat count, since several stage screens ignore held-key repeats.
     */
    private fun pageKeyEvent(source: KeyEvent, key: PageKey, action: Int) = KeyEvent(
        source.downTime,
        source.eventTime,
        action,
        key.keyCode,
        if (action == source.action) source.repeatCount else 0,
        source.metaState,
        KeyCharacterMap.VIRTUAL_KEYBOARD,
        key.scanCode,
        source.flags and KeyEvent.FLAG_LONG_PRESS.inv(),
        InputDevice.SOURCE_KEYBOARD,
    )

    private companion object {
        val ESCAPE = PageKey(KeyEvent.KEYCODE_ESCAPE, 1)
        val ENTER = PageKey(KeyEvent.KEYCODE_ENTER, 28)
        val SPACE = PageKey(KeyEvent.KEYCODE_SPACE, 57)

        /** Remote keys translated for the page. D-pad arrows already arrive as arrow keys. */
        val PAGE_KEYS = mapOf(
            KeyEvent.KEYCODE_DPAD_CENTER to ENTER,
            KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE to SPACE,
            KeyEvent.KEYCODE_MEDIA_PLAY to SPACE,
            KeyEvent.KEYCODE_MEDIA_PAUSE to SPACE,
        )
    }
}
