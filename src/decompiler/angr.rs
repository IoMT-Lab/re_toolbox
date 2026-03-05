use anyhow::Result;
use std::io::BufRead as _;
use std::io::BufReader;
use std::io::Read;
use std::{env, fs, io::Write as _, process::Command, str};
use tempfile;

pub fn list_functions(contents: &Vec<u8>) -> Result<Vec<String>> {
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(contents)?;

    let angr_dir = env::var("ANGR_DIR")?;
    let script = angr_dir.clone() + "/list_functions.py";

    let mut command = Command::new("pipenv");
    command
        .current_dir(angr_dir)
        .arg("run")
        .arg("python")
        .arg(script)
        .arg(tfile.path());

    match command.output() {
        Ok(resp) => {
            if let Some(0) = resp.status.code() {
                let mut return_file = String::from_utf8(resp.stdout)?;
                return_file.remove(return_file.len() - 1);
                let f = fs::File::open(&return_file)?;
                let functions = BufReader::new(f)
                    .lines()
                    .filter_map(|l| l.ok())
                    .collect::<Vec<String>>();

                Ok(functions)
            } else {
                println!("{}", String::from_utf8(resp.stderr)?);
                Ok(vec![])
            }
        }
        Err(e) => {
            println!("{:?}", e);
            Ok(vec![])
        }
    }
}

pub fn decompile_function(contents: &Vec<u8>, function_name: &str) -> Result<Vec<u8>> {
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(contents)?;

    let angr_dir = env::var("ANGR_DIR")?;
    let script = angr_dir.clone() + "/decomp.py";

    let mut command = Command::new("pipenv");
    command
        .current_dir(angr_dir)
        .arg("run")
        .arg("python")
        .arg(script)
        .arg(tfile.path())
        .arg(function_name);

    let res = command.output()?;
    let mut func = Vec::new();

    if let Some(0) = res.status.code() {
        let mut return_file = String::from_utf8(res.stdout)?;
        return_file.remove(return_file.len() - 1);
        let mut f = fs::File::open(&return_file)?;
        let _ = f.read_to_end(&mut func);
    }

    Ok(func)
}

pub fn decompile_all(contents: &Vec<u8>) -> Result<Vec<u8>> {
    let mut tfile = tempfile::NamedTempFile::new()?;
    tfile.write_all(contents)?;

    let angr_dir = env::var("ANGR_DIR")?;
    let script = angr_dir.clone() + "/decomp.py";

    let mut command = Command::new("pipenv");
    command
        .current_dir(angr_dir)
        .arg("run")
        .arg("python")
        .arg(script)
        .arg(tfile.path());
    let res = command.output()?;
    let mut decomp = Vec::new();

    if let Some(0) = res.status.code() {
        let mut return_file = String::from_utf8(res.stdout)?;
        return_file.remove(return_file.len() - 1);
        let mut f = fs::File::open(&return_file)?;
        let _ = f.read_to_end(&mut decomp);
    }

    Ok(decomp)
}
