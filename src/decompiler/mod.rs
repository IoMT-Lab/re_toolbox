use std::fmt::Display;

use anyhow::{anyhow, Result};
use clap::{Args, Subcommand, ValueEnum};

use crate::{Format, Workspace};

pub mod angr;
pub mod ghidra;

#[derive(Subcommand, Debug)]
pub enum DecompilerSubcommand {
    /// Display currently configured decompiler
    Get,

    /// Set current decompiler
    Set(DecompilerSetArgs),

    /// List available decompilers
    List,

    /// List functions present in binary, using current decompiler
    ListFunctions,

    /// Decompile function, using current decompiler
    Decompile(DecompileArgs),

    DiscoverDataStructures,

    /// Rebuild function's stack variable's structure
    StackStructRebuild(DecompileArgs),
}

#[derive(Args, Debug)]
pub struct DecompilerSetArgs {
    /// Decompiler to switch to
    decompiler: Decompiler
}

#[derive(Debug, Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum)]
pub enum Decompiler {
    Ghidra,
    Angr
}

impl Display for Decompiler {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", match self {
            Self::Angr => "Angr",
            Self::Ghidra => "Ghidra",
        })?;
        Ok(())
    }
}

#[derive(Args, Debug)]
pub struct DecompileArgs {
    /// Function to decompile
    function: String
}


impl DecompilerSubcommand {
    pub fn execute(&self, workspace: &mut Workspace) {
        match self {
            DecompilerSubcommand::Get => {
                println!("Current decompiler {}", workspace.decompiler);
            },
            DecompilerSubcommand::Set(decompiler_set_args) => {
                workspace.decompiler = decompiler_set_args.decompiler;
                println!("Decompiler changed to {}", decompiler_set_args.decompiler);
            }
            DecompilerSubcommand::List => {
                println!("Available decompilers: ");
                println!("  {}", Decompiler::Angr);
                println!("  {}", Decompiler::Ghidra);
            }
            DecompilerSubcommand::ListFunctions => {
                if let Some(workfile) = &workspace.active_file {
                    match workfile.format {
                        Format::Bytecode => {
                            println!("Running list_function from {}...", workspace.decompiler);
    
                            let function_names = match workspace.decompiler {
                                Decompiler::Ghidra => ghidra::list_functions(&workfile.contents),
                                Decompiler::Angr => angr::list_functions(&workfile.contents),
                            };
    
                            if let Ok(functions) = function_names {
                                for function in functions {
                                    println!("  {}", function);
                                }
                            } else {
                                println!("!! Unexpected error occurred !!");
                            } 
                        },
                        Format::Source => println!("!! Decompiler cannot be used on Source file !!"),
                    }
                } else {
                    println!("! No active file to decompile !");
                }
    
            },
            DecompilerSubcommand::Decompile(decompile_args) => {
                if let Some(workfile) = &mut workspace.active_file {
                    match workfile.format {
                        Format::Bytecode => {
                            println!("Decompiling function {} with {}... ", decompile_args.function, workspace.decompiler);
    
                            let function_names = match workspace.decompiler {
                                Decompiler::Ghidra => ghidra::decompile_function(&workfile.contents, &decompile_args.function),
                                Decompiler::Angr => {
                                    println!("!! Decompiling with Angr is not currently supported !!");
                                    Err(anyhow!("bad"))
                                }
                            };
    
                            if let Ok(source) = function_names {
                                println!("... Function decompiled");
                                println!("Replacing working file with new content");
    
                                workfile.format = Format::Source;
                                workfile.contents = source;
                                workfile.modified_since_load = true;
                                workfile.modified_since_last_save = true;
                            } else {
                                println!("!! Unexpected error occurred !!");
                            }
                        },
                        Format::Source => println!("!! Decompiler cannot be used on Source file !!"),
                    }
                } else {
                    println!("! No active file to decompile !");
                }
    
            },

            DecompilerSubcommand::DiscoverDataStructures => {
                if let Some(workfile) = &workspace.active_file {
                    match workfile.format {
                        Format::Bytecode => {
                            println!("Trying to find data structures from {}...", workspace.decompiler);

                            let result = match workspace.decompiler {
                                Decompiler::Ghidra => ghidra::run_struct_rebuilder(&workfile.contents),
                                _ => {Err("Angr is not supported for this analysis")}.expect("REASON")
                            };

                        },
                        Format::Source => println!("!! Decompiler cannot be used on Source file !!"),
                    }
                } else {
                    println!("! No active file to decompile !");
                }
            },


            DecompilerSubcommand::StackStructRebuild(decompile_args) => {
                if let Some(workfile) = &mut workspace.active_file {
                    match workfile.format {
                        Format::Bytecode => {
                            println!("Decompiling function {} with {}... ", decompile_args.function, workspace.decompiler);

                            let function_names = match workspace.decompiler {
                                Decompiler::Ghidra => ghidra::stack_struct_rebuild(&workfile.contents, &decompile_args.function),
                                Decompiler::Angr => {
                                    println!("!! Decompiling with Angr is not currently supported !!");
                                    Err(anyhow!("bad"))
                                }
                            };

                            if let Ok(source) = function_names {
                                println!("... Function decompiled");
                                println!("Replacing working file with new content");

                                workfile.format = Format::Source;
                                workfile.contents = source;
                                workfile.modified_since_load = true;
                                workfile.modified_since_last_save = true;
                            } else {
                                println!("!! Unexpected error occurred !!");
                            }
                        },
                        Format::Source => println!("!! Decompiler cannot be used on Source file !!"),
                    }
                } else {
                    println!("! No active file to decompile !");
                }
            }
        }
    }
}