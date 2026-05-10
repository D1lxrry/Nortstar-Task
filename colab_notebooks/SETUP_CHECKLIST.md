# Colab setup checklist for NorthStar

If you do not get distracted, this should take about 5 minutes end to
end. Each section below is self contained, so you can put this down
between any 2 sections and pick it back up later.

The MongoDB connection string and the Atlas cluster details further
down are already correct for my setup. Copy and paste rather than
retype, the password is fiddly.

## 1. Open the 3 tabs you need

Open 3 browser tabs and leave them up while you go through the rest
of this list:

- Atlas Network Access: <https://cloud.mongodb.com/v2/69e6304728a58f953d1569c0#/security/network/accessList>
- Google Drive root:    <https://drive.google.com/drive/my-drive>
- Google Colab home:    <https://colab.research.google.com/>

## 2. Atlas, allow Colab in

Colab runs out of Google Cloud, not from your laptop, so its outbound
IP is not on Atlas's allow list yet. In the Atlas Network Access tab,
hit `ADD IP ADDRESS` (top right), then `ALLOW ACCESS FROM ANYWHERE`.
Atlas fills in `0.0.0.0/0` for you. If you only need access for the
demo, tick `Temporary 7 days`, otherwise leave it permanent. Click
`Confirm`. The entry can be revoked afterwards without breaking
anything else.

## 3. Drive, upload the notebooks folder

Find the `colab_notebooks` folder inside the coursework workspace in
Finder. Drag the whole folder onto the Drive web page and drop it
into the root of `My Drive`. Wait for the upload indicator (bottom
right of Drive) to finish. The README and the launcher come along
for the ride, that does no harm.

## 4. Colab, open notebook 01 from Drive

In Colab, `File` then `Open notebook`. Switch to the `Google Drive`
tab in the dialog and double click `01_mongodb_pipeline.ipynb` inside
`colab_notebooks/`. The notebook opens, but do not press Run yet, the
secret needs to be in place first.

## 5. Add the MONGODB_URI secret

In the open notebook, click the key icon in the left sidebar to open
the Secrets pane. Click `+ Add new secret`. Name it `MONGODB_URI` and
paste the connection string below as the value:

```
mongodb+srv://larryco211_db_user:ud9FGTzMgygYgBVb@northstar.qltsnwd.mongodb.net/?appName=NorthStar
```

Then flip the `Notebook access` toggle ON. The notebook reads the URI
via `userdata.get('MONGODB_URI')`, which keeps the password out of the
source code.

## 6. Run the first notebook

Now you can run it. `Runtime` then `Run all`. The first cell mounts
Drive, click through the consent dialog when it pops. Then sit back,
end to end is about 5 minutes. A clean run ends with
`orders_aggregate documents inserted: 1250` and the analytical
queries print their results inline.

## 7. Run the rest

Notebooks 02 to 05 open the same way: `File`, `Open notebook`,
`Google Drive` tab, double click. Notebooks 03 and 04 use the R
kernel rather than Python, so before running either of them switch
the runtime via `Runtime`, `Change runtime type`, `R`. The 9 CSVs
are pulled from the GitHub repo over HTTPS by the first code cell
of each notebook, so no upload step is needed. Notebook 04 no
longer depends on 03 having been run first because it rebuilds the
SQLite file at runtime from the same raw URLs.

## 8. Optional, GitHub for a 1 click run path

If you want the marker to launch a notebook from a single link, push
`colab_notebooks/` to a public GitHub repo. Each notebook then has a
URL of the shape
`https://github.com/USER/REPO/blob/main/colab_notebooks/01_mongodb_pipeline.ipynb`.
Swap `github.com` for `colab.research.google.com/github` in that URL
and Colab opens the notebook directly. This is the workflow the
rubric calls out as the GitHub plus Colab deliverable.

## Things that go wrong

| Symptom                                                       | Fix                                                                                                |
|---------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| Atlas page asks me to log in                                  | Sign in with the same Google account you registered with Atlas.                                    |
| Atlas says my IP is not on the allow list                     | Step 2 was skipped, or the rule has expired. Add `0.0.0.0/0` again.                                |
| Drive shows "uploading" forever                                | Check the network. Reload Drive, drag the folder again.                                            |
| Colab cell errors with `MONGODB_URI is None`                   | Notebook access toggle was off. Open the Secrets pane, toggle it on, rerun the cell.               |
| Colab cell errors with bad auth                                | Wrong password. Reset in Atlas under Database Access, then update the Secret.                      |
| R notebook says package not installed                          | Runtime is still on Python. `Runtime` -> `Change runtime type` -> `R`, rerun the setup cell.        |
| `northstar.sqlite` not found in notebook 04                    | Old version of notebook 04 (relied on notebook 03). The current version is self contained.         |
| `Cannot open URL ... 404 Not Found` in notebook 03 or 04       | The repo branch has moved or the CSVs are not at `northstar_dataset/`. Check the `base_url` in the first code cell. |
