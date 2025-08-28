use anyhow::Result;
use std::io::Read;
use std::path::PathBuf;
use std::{env, fs, io::Write as _, process::Command, str};
use tempfile;

pub fn list_functions(contents: &Vec<u8>) -> Result<Vec<String>> {
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(contents)?;

    let ghidra_dir = env::var("GHIDRA_DIR")?;
    let command_path = ghidra_dir.clone() + "/ghidra_run.py";
    let stdout_file = tempfile::NamedTempFile::new()?;

    let res = Command::new(command_path)
        .arg(tfile.path())
        .arg("ListFunctionsH.java")
        .arg("--stdout_file")
        .arg(stdout_file.path())
        .output()?;

    if let Some(0) = res.status.code() {
        let mut output = String::new();
        stdout_file.as_file().read_to_string(&mut output)?;
        let lines = output.split('\n');

        let functions = lines
            .filter(|s| s.starts_with("INFO  ListFunctionsH.java>"))
            .map(|s| s.trim_start_matches("INFO  ListFunctionsH.java> "))
            .map(|s| s.trim_end_matches(" (GhidraScript)  "))
            .map(|s| s.to_owned())
            .collect::<Vec<String>>();
        Ok(functions)
    } else {
        Ok(vec![])
    }
}

pub fn decompile_function(contents: &Vec<u8>, function_name: &str) -> Result<Vec<u8>> {
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(contents)?;

    let ghidra_dir = env::var("GHIDRA_DIR")?;
    let command_path = ghidra_dir.clone() + "/ghidra_run.py";
    let stdout_file = tempfile::NamedTempFile::new()?;

    let res = Command::new(command_path)
        .arg(tfile.path())
        .arg("DecompileFunctionH.java")
        .arg("--extra_args")
        .arg(function_name)
        .arg("--stdout_file")
        .arg(stdout_file.path())
        .output()?;

    let mut func = Vec::new();
    if let Some(0) = res.status.code() {
        let mut output = String::new();
        stdout_file.as_file().read_to_string(&mut output)?;
        let lines = output.split('\n');

        let mut in_decomp = false;
        for line in lines {
            if line.starts_with("INFO  DecompileFunctionH.java>") {
                in_decomp = true;
            } else if line.contains("(GhidraScript)") {
                break;
            } else if in_decomp {
                func.extend(line.as_bytes());
                func.push(b'\n');
            }
        }
    }
    Ok(func)
}

pub fn decompile_all(contents: &Vec<u8>) -> Result<Vec<u8>> {
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(contents)?;

    let ghidra_dir = env::var("GHIDRA_DIR")?;
    let command_path = ghidra_dir.clone() + "/ghidra_run.py";
    let stdout_file = tempfile::NamedTempFile::new()?;

    let res = Command::new(command_path)
        .arg(tfile.path())
        .arg("DecompileFile.java")
        .arg("--extra_args")
        .arg("--stdout_file")
        .arg(stdout_file.path())
        .output()?;

    let mut decomp = Vec::new();
    if let Some(0) = res.status.code() {
        let mut output = String::new();
        stdout_file.as_file().read_to_string(&mut output)?;
        let lines = output.split('\n');

        let mut in_decomp = false;
        for line in lines {
            if line.starts_with("INFO  DecompileFile.java>") {
                if line.contains("DONE (GhidraScript)") {
                    break;
                }
                in_decomp = true;
            } else if line.contains("(GhidraScript)") {
                in_decomp = false;
                decomp.push(b'\n');
            } else if in_decomp {
                decomp.extend(line.as_bytes());
                decomp.push(b'\n');
            }
        }
    }
    Ok(decomp)
}
