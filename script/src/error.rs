use std::convert::From;

#[derive(Clone)]
pub enum Error {
    Failure,
    WorkerShutdown,
    MalformedPayload(String),
    ResourceUnavailable,
    InternalError(String),
    Superseded,
    IntermittentTask,
}

impl From<std::io::Error> for Error {
    fn from(err: std::io::Error) -> Error {
        Error::InternalError(format!("{}", err))
    }
}

impl From<serde_yaml::Error> for Error {
    fn from(err: serde_yaml::Error) -> Error {
        Error::InternalError(format!("{}", err))
    }
}

impl Error {
    pub(crate) fn exit_code(self) -> i32 {
        match self {
            Self::Failure => 1,
            Self::WorkerShutdown => 2,
            Self::MalformedPayload(_) => 3,
            Self::ResourceUnavailable => 4,
            Self::InternalError(_) => 5,
            Self::Superseded => 6,
            Self::IntermittentTask => 7,
        }
    }

    #[allow(dead_code)]
    pub(crate) fn description(self) -> &'static str {
        match self {
            Self::Failure => "failure",
            Self::WorkerShutdown => "worker-shutdown",
            Self::MalformedPayload(_) => "malformed-payload",
            Self::ResourceUnavailable => "resource-unavailable",
            Self::InternalError(_) => "internal-error",
            Self::Superseded => "superseded",
            Self::IntermittentTask => "intermittent-task",
        }
    }
}

/*
impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f,
    }
}
*/
