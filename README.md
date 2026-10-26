# Patchwork

Patchwork is a review-first code repair studio. Describe a bug, choose a source file, and ask NVIDIA Nemotron to propose a focused repair. Patchwork displays the unified diff and complete replacement so you can inspect the suggestion before applying it.

Patchwork calls NVIDIA Nemotron through Nebius Token Factory's OpenAI-compatible chat completions API. The default model is `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`.

## Run locally

Requires Python 3.10 or newer and a Nebius Token Factory API key with access to the configured model.

In PowerShell, open this folder and run:

```powershell
python app.py
```

Open <http://127.0.0.1:8000>, paste your Token Factory key into the connection panel, and use a sample project or upload a ZIP. In local mode, the key stays in the server process's memory and is cleared when it stops. Set `NEBIUS_MODEL` before launching to select another model available to your account.

## Deploy a public demo on Render

The included `render.yaml` configures a Render web service. To deploy:

1. Push this folder to a public GitHub repository.
2. In Render, choose **New > Blueprint** and connect the repository.
3. When Render prompts for `NEBIUS_API_KEY`, enter the Token Factory key in the private environment-variable field. Never add the key to the repository or a browser setting.
4. Deploy the `patchwork-demo` web service and open its generated `onrender.com` URL.
5. Confirm `/api/status` reports the model connection, then make a sample patch request from the UI.

Hosted mode reads the API key from the service environment, hides the local key-entry form, and refuses API-key changes from the public page. Patch requests are capped per client IP per hour by `PATCHWORK_REQUESTS_PER_HOUR` (12 by default) to protect the demo credential. Uploaded project files are processed in memory and are not written to disk. Render's free web services can sleep when idle and may take about a minute to wake on the next visit.

To deploy manually instead of using the Blueprint, configure a Python web service with build command `pip install -r requirements.txt` and start command `python app.py`. Set `PATCHWORK_DEMO_MODE=true`, `NEBIUS_API_KEY` as a secret, and optionally `NEBIUS_MODEL`. The app binds to `0.0.0.0` and uses the `PORT` supplied by the host in hosted mode.

## Use Patchwork

Choose a bundled example or upload a ZIP archive. Patchwork accepts archives up to 2 MB and inspects up to 40 UTF-8 text files of common source, configuration, and documentation types. Select the relevant file, describe expected and actual behaviour, then choose **Propose a patch**. Review the diff and replacement, then copy or download the suggested source.

Uploaded source is treated as text. Patchwork does not execute uploaded code, generated code, or the bundled sample tests. Validate proposed changes in your own development environment.

## Project structure

- `app.py` serves the local or hosted UI and API, inspects ZIP uploads, and calls Nebius Token Factory.
- `index.html` contains the responsive interface, sample selection, drag-and-drop upload, diff review, and replacement export actions.
- `sample/` contains example source files and reference tests. Patchwork does not run those tests.
- `render.yaml` describes the Render demo service.

## License

MIT. See [LICENSE](LICENSE).

