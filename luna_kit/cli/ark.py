import os
from argparse import ArgumentParser, Namespace

from rich.progress import Progress, track

from ..console import console
from ._actions import GlobFiles
from .cli import CLI, CLICommand


@CLI.register_command
class ARKParser(CLICommand):
    COMMAND = 'ark'
    HELP = 'Extract .ark files'
    
    @classmethod
    def build_args(cls, parser: ArgumentParser):
        parser.add_argument(
            'files',
            nargs = '+',
            help = 'input .ark files',
            action = GlobFiles,
        )
        
        parser.add_argument(
            '-s', '--separate-folders',
            dest = 'separate_folders',
            help = 'Output each .ark file in not separate folders',
            action = 'store_true',
        )
        
        parser.add_argument(
            '-o', '--output',
            dest = 'output',
            help = 'output directory for .ark file(s)',
        )
        
        parser.add_argument(
            '-i', '--ignore-errors',
            dest = 'ignore_errors',
            action = 'store_true',
            help = 'ignore errors',
        )
        
        parser.add_argument(
            '-v', '--data-version',
            dest = 'data_version',
            action = 'store_true',
            help = 'print data version from ark files',
        )

        parser.add_argument(
            '-f', '--filter-files',
            nargs = '+',
            dest = 'filter_files',
            help = 'filter files from ark files',
        )

        parser.add_argument(
            '-r', '--rename-force',
            dest = 'rename_force',
            help = 'if len filter-files 1, rename output file to name input .ark file',
            action = 'store_true',
        )
    
    @classmethod
    def run_command(cls, args: Namespace):
        import os
        
        from ..ark import ARK
        from ..ark_filename import sort_ark_filenames
            
        output = './'
        
        files: list[str] = args.files
        
        files = sort_ark_filenames(files)
        
        if len(files) == 0:
            console.print('[red]No files found[/]')
            return
        
        if args.output:
            output = args.output
        elif len(files) == 1:
            output = os.path.splitext(os.path.basename(args.files[0]))[0]
        
        def extract_all(ark_file: ARK, output: str, ark_name: str):
            failed = []
            
            for file_metadata in track(
                ark_file.files,
                console = console,
                description = 'Extracting...',
            ):
                console.print(f'extracting: [yellow]{file_metadata.full_path}[/yellow]')
                try:
                    file = ark_file.read_file(file_metadata)
                    name = file_metadata.full_path

                    if args.filter_files and len(args.filter_files) == 1 and args.rename_force:
                        name = os.path.splitext(ark_name)[0] + os.path.splitext(file_metadata.full_path)[1]

                    file.save(os.path.join(output, name))
                except Exception as e:
                    if args.ignore_errors:
                        failed.append(file_metadata.full_path)
                        console.print(f'[red]could not extract {file_metadata.full_path}[/red]')
                        continue
                    else:
                        e.add_note(f'file: {file_metadata.full_path}')
                        raise e
            
            return failed
        
        versions = {}
        
        if len(files) == 1:
            console.print(f'Opening: [yellow]{files[0]}[/]')

            with ARK(files[0], args.filter_files) as ark_file:
                if args.data_version:
                    version = ark_file.data_version
                    if version:
                        versions[files[0]] = version
                if not args.data_version or args.output:
                    output = os.path.dirname(files[0])

                    if args.separate_folders:
                        path = output
                    else:
                        path = os.path.join(output, os.path.splitext(os.path.basename(files[0]))[0])

                    failed = extract_all(ark_file, path, files[0])
        else:
            failed: dict[str, list[str]] = {}
            for filename in files:
                filename: str

                output = os.path.dirname(filename)

                if args.separate_folders:
                    path = output
                else:
                    path = os.path.join(output, os.path.splitext(os.path.basename(filename))[0])
                
                console.print(f'Opening: [yellow]{filename}[/]')
                with ARK(filename, args.filter_files) as ark_file:
                    if args.data_version:
                        version = ark_file.data_version
                        if version:
                            versions[filename] = version
                    if not args.data_version or args.output:
                        failed[filename] = extract_all(ark_file, path, filename)
            
            if len(failed) > 0:
                for arkfile, files in failed.items():
                    for file in files:
                        console.print(f'[red]failed to extract {file} from {arkfile}')

        if args.data_version:
            if len(versions):
                if len(versions) == 1:
                    console.print(list(versions.values())[0])
                else:
                    for filename, version in versions.items():
                        console.print(f'{os.path.basename(filename)}: {version}')
            else:
                console.print("[red]could not find version[/]")
                        
