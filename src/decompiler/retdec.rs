use anyhow::Result;
use serde_json::{self, Value};
use std::fs::File;
use std::io::BufRead as _;
use std::io::BufReader;
use std::io::Read;
use std::{env, fs, io::Write as _, process::Command, str};
use tempfile;

pub fn list_functions(contents: &Vec<u8>) -> Result<Vec<String>> {
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(contents)?;

    let retdec_path = env::var("RETDEC_PATH")?;
    let output_dir = tempfile::tempdir()?;
    let output_file = output_dir.into_path().join("output.c");

    let mut command = Command::new(retdec_path);
    command
        .arg("--output")
        .arg(output_file.clone())
        .arg("--silent")
        .arg(tfile.path());

    let res = command.output()?;
    if let Some(0) = res.status.code() {
        println!("{:?}", output_file.clone());
        let json_file = output_file.with_extension("config.json");
        let file = File::open(json_file)?;
        let reader = BufReader::new(file);

        // Read the JSON contents of the file as an instance of `User`.
        let json: Value = serde_json::from_reader(reader)?;
        let function_obj = json.get("functions").unwrap();
        let function_list = function_obj
            .as_array()
            .unwrap()
            .iter()
            .map(|f| f.get("name").unwrap().as_str().unwrap().to_string())
            .collect();
        Ok(function_list)
    } else {
        Ok(vec![])
    }
}

pub fn decompile_function(contents: &Vec<u8>, function_name: &str) -> Result<Vec<u8>> {
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(contents)?;

    let retdec_path = env::var("RETDEC_PATH")?;
    let output_dir = tempfile::tempdir()?;
    let output_file = output_dir.into_path().join("output.c");

    let mut command = Command::new(retdec_path);
    command
        .arg("--output")
        .arg(output_file.clone())
        .arg("--silent")
        .arg("--select-functions")
        .arg(function_name)
        .arg(tfile.path());

    let res = command.output()?;
    let mut func = Vec::new();

    if let Some(0) = res.status.code() {
        let mut f = fs::File::open(&output_file)?;
        let _ = f.read_to_end(&mut func);
    }

    Ok(func)
}

pub fn decompile_all(contents: &Vec<u8>) -> Result<Vec<u8>> {
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(contents)?;

    let retdec_path = env::var("RETDEC_PATH")?;
    let output_dir = tempfile::tempdir()?;
    let output_file = output_dir.into_path().join("output.c");

    let mut command = Command::new(retdec_path);
    command
        .arg("--output")
        .arg(output_file.clone())
        .arg("--silent")
        .arg(tfile.path());

    let res = command.output()?;
    let mut decomp = Vec::new();

    if let Some(0) = res.status.code() {
        let mut f = fs::File::open(&output_file)?;
        let _ = f.read_to_end(&mut decomp);
    }

    Ok(decomp)
}
