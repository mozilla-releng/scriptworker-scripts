use scriptworker_script::{get_artifact_path, Task};
use serde_derive::Deserialize;
use std::path::{Path, PathBuf};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    google_project: String,
    flank_jar: PathBuf,
    flank_config: PathBuf,
}

fn do_work(
    config: Config,
    work_dir: &Path,
    task: Task<Attr, Extra>,
) -> Result<(), Box<dyn std::error::Error>> {
    for upstream in &task.payload.upstream_artifacts {
        match &*upstream.paths {
            [apk, test] => println!(
                "{:?}",
                vec![
                    "java",
                    "-jar",
                    config.flank_jar.to_string_lossy().as_ref(),
                    "--config",
                    config.flank_config.to_string_lossy().as_ref(),
                    "--project",
                    &config.google_project,
                    "--max-test-shards",
                    /* upstream.max_test_shards */ "-1",
                    "--apk",
                    get_artifact_path(&upstream.task_id, &apk, work_dir)
                        .to_string_lossy()
                        .as_ref(),
                    "--test",
                    get_artifact_path(&upstream.task_id, &test, work_dir)
                        .to_string_lossy()
                        .as_ref(),
                    // FIXME
                ]
            ),
            _ => panic!("Did not provide correct number of apks!"),
        }
    }
    Ok(())
}

#[derive(Deserialize, Debug)]
struct Devices {
    model: String,
    version: u32,
}

#[derive(Deserialize, Debug)]
struct Attr {
    devices: Vec<Devices>,
}

#[derive(Deserialize, Debug)]
struct Extra {
    results_bucket: String,
    directories_to_pull: Vec<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    scriptworker_script::main(do_work)
}
