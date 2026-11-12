package dev.openkaraoke.stage

import android.os.Bundle
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

/** Points the app at another server (the dev server) without reinstalling. */
class ServerAddressActivity : AppCompatActivity() {

    private lateinit var field: EditText
    private lateinit var error: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_server_address)

        field = findViewById(R.id.server_address)
        error = findViewById(R.id.server_error)

        field.setText(ServerAddress.get(this))
        field.setSelection(field.text.length)
        field.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_DONE) {
                save()
                true
            } else {
                false
            }
        }

        findViewById<Button>(R.id.server_save).setOnClickListener { save() }
        findViewById<Button>(R.id.server_reset).apply {
            text = getString(R.string.server_reset, ServerAddress.label(ServerAddress.DEFAULT))
            setOnClickListener {
                ServerAddress.reset(this@ServerAddressActivity)
                setResult(RESULT_OK)
                finish()
            }
        }
    }

    private fun save() {
        val address = ServerAddress.normalize(field.text.toString())
        if (address == null) {
            error.visibility = View.VISIBLE
            return
        }
        ServerAddress.set(this, address)
        setResult(RESULT_OK)
        finish()
    }
}
