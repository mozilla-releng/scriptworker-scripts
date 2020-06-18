use scriptworker_script::{Context, Error, Task};
use serde_derive::Deserialize;
use std::collections::HashMap;
use std::os::unix::process::ExitStatusExt;
use std::process::Command;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    #[serde(
        alias = "project_config_file",
        deserialize_with = "scriptworker_script::load_secrets"
    )]
    projects: HashMap<String, Project>,
    #[serde(alias = "taskcluster_scope_prefix")]
    scope_prefix: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Project {
    api_token: String,
    repository_url: String,
}

#[derive(Deserialize, Debug)]
struct Attr {
    project: String,
}

#[derive(Deserialize, Debug)]
struct Extra {
    action: String,
}

fn verify_payload(config: &Config, _: &Context, task: &Task<Attr, Extra>) -> Result<(), Error> {
    if task.payload.extra.action != "upload" {
        return Err(Error::MalformedPayload(format!(
            "Unsupported action: {}",
            task.payload.extra.action
        )));
    }

    task.require_scopes(task.payload.upstream_artifacts.iter().map(|upstream| {
        let project_name = &upstream.attributes.project;
        format!("{}:pypi:project:{}", config.scope_prefix, project_name)
    }))
}

fn run_command(mut command: Command, action: &dyn Fn() -> String) -> Result<(), Error> {
    println!("Running: {:?}", command);
    match command.status() {
        Ok(result) => {
            if !result.success() {
                println!(
                    "Failed to {}: {}",
                    action(),
                    match (result.code(), result.signal()) {
                        (Some(code), _) => format!("exit code {}", code),
                        (_, Some(signal)) => format!("exited with signal {}", signal),
                        (None, None) => "unknown exit reason".to_string(),
                    }
                );
                return Err(Error::Failure);
            }
            Ok(())
        }
        Err(err) => {
            println!("Failed to start command: {:?}", err);
            Err(Error::Failure)
        }
    }
}

impl Config {
    fn get_project(&self, project_name: &str) -> Result<&Project, Error> {
        self.projects.get(project_name).ok_or_else(|| {
            Error::MalformedPayload(format!("Unknown pypi project {}", project_name))
        })
    }
}

#[scriptworker_script::main]
fn do_work(config: Config, context: &Context, task: Task<Attr, Extra>) -> Result<(), Error> {
    verify_payload(&config, &context, &task)?;

    task.payload
        .upstream_artifacts
        .iter()
        .map(|upstream| -> Result<(), Error> {
            let project_name = &upstream.attributes.project;
            // Ensure project exists
            config.get_project(project_name)?;

            let mut command = Command::new("twine");
            command.arg("check");
            for artifact in &upstream.paths {
                command.arg(artifact.file_path(context));
            }
            run_command(command, &|| format!("upload files for {}", project_name))
        })
        .fold(Ok(()), Result::or)?;

    for upstream in &task.payload.upstream_artifacts {
        let project_name = &upstream.attributes.project;
        let project = config.get_project(project_name)?;

        println!(
            "Uploading {} from task {} to {} for project {}",
            &upstream
                .paths
                .iter()
                .map(|p| p.task_path().to_string_lossy())
                .collect::<Vec<_>>()
                .join(", "),
            &upstream.task_id,
            project.repository_url,
            project_name
        );

        // To use tokens with PyPI, set the username to `__token__` and the password to the token.
        // See https://pypi.org/help/#apitoken
        let mut command = Command::new("twine");
        command
            .arg("upload")
            .arg("--user")
            .arg("__token__")
            .arg("--repository-url")
            .arg(&project.repository_url);
        for artifact in &upstream.paths {
            command.arg(artifact.file_path(context));
        }
        command.env("TWINE_PASSWORD", &project.api_token);
        run_command(command, &|| format!("upload files for {}", project_name))?;
    }
    Ok(())
}
