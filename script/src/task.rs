use std::path::{Path, PathBuf};

use serde::de::DeserializeOwned;
use serde_derive::Deserialize;

use crate::error::Error;
use crate::Context;

#[derive(Deserialize, Debug)]
pub struct Empty {}

#[derive(Debug)]
pub struct TaskArtifacts<A> {
    pub task_type: String,
    pub task_id: String,
    // TODO: Figure out how to thread work dir here
    // so we don't need to pass the context to get it.
    pub paths: Vec<ArtifactPath>,
    pub attributes: A,
}

impl<'de, A> serde::Deserialize<'de> for TaskArtifacts<A>
where
    A: serde::Deserialize<'de>,
{
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        #[derive(Deserialize)]
        #[serde(rename_all = "camelCase")]
        struct RawArtifacts<A> {
            pub task_type: String,
            pub task_id: String,
            // TODO: Path
            pub paths: Vec<PathBuf>,
            #[serde(flatten)]
            pub attributes: A,
        }
        let raw: RawArtifacts<A> = serde::Deserialize::deserialize(deserializer)?;
        let task_id = raw.task_id.clone();
        let paths = raw
            .paths
            .into_iter()
            .map(|path| {
                if path.is_absolute() {
                    Err(serde::de::Error::custom(
                        "Cannot sepecify absolute path in upstreamArtifacts.",
                    ))
                } else {
                    Ok(ArtifactPath {
                        task_id: task_id.clone(),
                        path,
                    })
                }
            })
            .collect::<Result<_, _>>()?;
        Ok(TaskArtifacts::<A> {
            task_type: raw.task_type,
            task_id: raw.task_id,
            paths,
            attributes: raw.attributes,
        })
    }
}

#[derive(Debug)]
pub struct ArtifactPath {
    task_id: String,
    path: PathBuf,
}

impl ArtifactPath {
    pub fn task_path(&self) -> &PathBuf {
        &self.path
    }
    pub fn file_path(&self, context: &Context) -> PathBuf {
        context
            .work_dir
            .join("cot")
            .join(&self.task_id)
            .join(&self.path)
    }
}

#[derive(Deserialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct TaskPayload<A, E> {
    pub upstream_artifacts: Vec<TaskArtifacts<A>>,
    #[serde(flatten)]
    pub extra: E,
}

#[derive(Deserialize, Debug)]
pub struct Task<A = Empty, E = Empty> {
    pub dependencies: Vec<String>,
    pub scopes: Vec<String>,
    pub payload: TaskPayload<A, E>,
}

impl<Attr, Extra> Task<Attr, Extra> {
    pub(crate) fn load<A, E>(filename: &Path) -> Result<Task<A, E>, Error>
    where
        A: DeserializeOwned,
        E: DeserializeOwned,
    {
        let file = std::fs::File::open(filename)
            .map_err(|_| Error::InternalError("Could not open task definition.".to_string()))?;
        Ok(serde_json::from_reader(file).map_err(|err| {
            Error::MalformedPayload(format!("Could not parse task payload: {}", err))
        })?)
    }

    pub fn require_scope(&self, scope: &str) -> Result<(), Error> {
        if self.scopes.iter().any(|x| x == scope) {
            Ok(())
        } else {
            Err(Error::MalformedPayload(format!("missing scope {}", scope)))
        }
    }

    pub fn require_scopes(&self, scopes: impl IntoIterator<Item = String>) -> Result<(), Error> {
        let missing_scopes: Vec<_> = scopes
            .into_iter()
            .filter(|scope| self.scopes.iter().all(|x| x != scope))
            .collect();
        if missing_scopes.is_empty() {
            Ok(())
        } else {
            Err(Error::MalformedPayload(format!(
                "missing scopes: {:?}",
                missing_scopes
            )))
        }
    }
}
