use std::{
    fs,
    io::{Read as _, Write as _},
    path::{Path, PathBuf},
    process::Command,
};

use anyhow::{anyhow, Result};
use clap::ValueEnum;
use once_cell::sync::OnceCell;
use walkdir::{IntoIter, WalkDir};
use yaml_rust2::yaml;

use crate::{Format, Workfile, Workspace};

mod subcommand;
pub use subcommand::ToolSubcommand;

static TOOLS: OnceCell<Vec<Tool>> = OnceCell::new();

#[derive(Debug, Clone)]
pub struct Tool {
    name: String,
    description: String,
    input: Format,
    output: Option<Format>,
    command: Specialization,
}

impl Tool {
    fn load(path: &impl AsRef<Path>) -> Result<Self> {
        let mut file = fs::File::open(path)?;
        let mut s = String::new();
        file.read_to_string(&mut s)?;

        let docs = yaml::YamlLoader::load_from_str(&s)?;
        let doc = &docs[0];

        let name = doc["name"].as_str().ok_or_else(|| anyhow!("ahh"))?;
        let description = doc["description"].as_str().ok_or_else(|| anyhow!("ahh"))?;
        let input_type = doc["input_type"].as_str().ok_or_else(|| anyhow!("ahh"))?;
        let input_type = Format::from_str(input_type, true).map_err(|e| anyhow!("ahh"))?;
        let output_type = match doc["output_type"].as_str() {
            Some(out) => Format::from_str(out, true).ok(),
            None => None,
        };
        let command = {
            match doc["type"].as_str().ok_or_else(|| anyhow!("ahh"))? {
                "bash" => {
                    let command = doc["command"].as_str().ok_or_else(|| anyhow!("ahh"))?;
                    Ok(Specialization::Bash {
                        command: command.to_owned(),
                    })
                }
                "python" => {
                    let workdir = doc["workdir"].as_str().ok_or_else(|| anyhow!("ahh"))?;
                    let script = doc["script"].as_str().ok_or_else(|| anyhow!("ahh"))?;
                    Ok(Specialization::Python {
                        workdir: workdir.to_owned(),
                        script: script.to_owned(),
                    })
                }
                _ => Err(anyhow!("Unknown specialization")),
            }
        }?;

        Ok(Self {
            name: name.to_owned(),
            description: description.to_owned(),
            input: input_type,
            output: output_type,
            command,
        })
    }

    pub fn details(&self) -> String {
        format!(
            "
        \tName: {}
        \tDescription: {}
        \tInput Format: {:?}
        \tOutput Format: {:?}",
            self.name, self.description, self.input, self.output
        )
    }

    pub fn run(&self, workspace: &mut Workspace) -> Result<()> {
        match &mut workspace.active_file {
            Some(workfile) if workfile.format == self.input => {
                let mut tfile = tempfile::NamedTempFile::new()?;
                tfile.write_all(&workfile.contents)?;

                let mut output = self.command.run(Some(tfile.path()))?;
                output.remove(output.len() - 1);
                let filename = output.split_inclusive('\n').last().unwrap();
                let mut f = fs::File::open(&filename)?;
                let mut new_contents = Vec::new();
                f.read_to_end(&mut new_contents)?;

                match self.output {
                    Some(format) => {
                        workfile.contents = new_contents;
                        workfile.format = format;
                        workfile.modified_since_load = true;
                        workfile.modified_since_last_save = true;
                    }
                    None => {
                        let output = String::from_utf8(new_contents)?;
                        println!("{}", output);
                    }
                }
                Ok(())
            }
            Some(Workfile { format, .. }) if format != &self.input => {
                Err(anyhow!("File format does not match required tool input"))
            }
            None => Err(anyhow!("No file to operate on")),
            _ => Err(anyhow! {"Problem with the file format"}),
        }
    }
}

#[derive(Debug, Clone)]
pub enum Specialization {
    Bash { command: String },
    Python { workdir: String, script: String },
}

impl Specialization {
    pub fn run(&self, input_file: Option<&Path>) -> Result<String> {
        match self {
            Self::Bash { command } => {
                let mut command = Command::new(command);
                if let Some(file) = input_file {
                    command.arg(file);
                }

                match command.output() {
                    Ok(resp) => {
                        println!("Tool completed with status: {:?}", resp.status);
                        if let Some(0) = resp.status.code() {
                            Ok(String::from_utf8(resp.stdout)?)
                        } else {
                            Err(anyhow!(
                                "Tool did not execute successfully: {:?}",
                                std::str::from_utf8(&resp.stderr)?
                            ))
                        }
                    }
                    Err(e) => Err(anyhow!("Problem executing tool: {:?}", e)),
                }
            }
            Self::Python { workdir, script } => {
                let mut command = Command::new("pipenv");
                command
                    .current_dir(workdir)
                    .arg("run")
                    .arg("python")
                    .arg(script);

                if let Some(file) = input_file {
                    command.arg(file);
                }

                match command.output() {
                    Ok(resp) => {
                        println!("Tool completed with status: {:?}", resp.status);
                        if let Some(0) = resp.status.code() {
                            Ok(String::from_utf8(resp.stdout)?)
                        } else {
                            Err(anyhow!(
                                "Tool did not execute successfully: {:?}",
                                std::str::from_utf8(&resp.stderr)?
                            ))
                        }
                    }
                    Err(e) => Err(anyhow!("Problem executing tool: {:?}", e)),
                }
            }
        }
    }
}

pub fn load_tools(directory: &impl AsRef<Path>) {
    let mut tools = Vec::new();
    for file in yaml_iter(directory) {
        match Tool::load(&file) {
            Ok(tool) => tools.push(tool),
            Err(e) => println!("WARN: tool failed to load {}", e),
        }
    }

    let _ = TOOLS.set(tools);
}

fn yaml_iter(
    directory: &impl AsRef<Path>,
) -> std::iter::Filter<
    std::iter::Map<
        std::iter::FilterMap<
            IntoIter,
            impl FnMut(Result<walkdir::DirEntry, walkdir::Error>) -> Option<walkdir::DirEntry>,
        >,
        impl FnMut(walkdir::DirEntry) -> PathBuf,
    >,
    impl FnMut(&PathBuf) -> bool,
> {
    WalkDir::new(directory)
        .into_iter()
        .filter_map(|e| e.ok())
        .map(|e| e.into_path())
        .filter(|p| {
            if let Some(ext) = p.extension().and_then(|ext| Some(ext.to_ascii_lowercase())) {
                match ext.to_str() {
                    Some("yml") => true,
                    Some("yaml") => true,
                    _ => false,
                }
            } else {
                false
            }
        })
}
