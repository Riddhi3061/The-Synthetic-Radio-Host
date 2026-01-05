"""
Command-line interface for The Synthetic Radio Host.

Usage:
    python -m src.main --topic "Mumbai Indians" --output "output/show.mp3"
"""

import argparse
import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="🎙️ The Synthetic Radio Host - Generate Hinglish radio shows from Wikipedia",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main --topic "Mumbai Indians"
  python -m src.main --topic "Shah Rukh Khan" --duration 3 --output "srk_show.mp3"
  python -m src.main --topic "Indian cuisine" --script-only
  python -m src.main --topic "https://en.wikipedia.org/wiki/Virat_Kohli"
  python -m src.main --from-script "output/show.txt" --output "output/show.mp3"
        """
    )
    
    parser.add_argument(
        "--topic", "-t",
        required=True,
        help="Wikipedia topic OR URL (e.g., 'Mumbai Indians' or 'https://en.wikipedia.org/wiki/Mumbai_Indians')"
    )
    
    parser.add_argument(
        "--duration", "-d",
        type=float,
        default=2.0,
        help="Target duration in minutes (default: 2.0)"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: output/<topic>_show.mp3)"
    )
    
    parser.add_argument(
        "--script-only",
        action="store_true",
        help="Generate script only (no audio)"
    )
    
    parser.add_argument(
        "--from-script", "-f",
        help="Generate audio from existing script file (skip Wikipedia & LLM)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Keep temporary files after generation"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Print header
    console.print(Panel.fit(
        "[bold cyan]🎙️ The Synthetic Radio Host[/bold cyan]\n"
        "[dim]Transform Wikipedia into Hinglish radio conversations[/dim]",
        border_style="cyan"
    ))
    
    try:
        # Import here to avoid slow startup
        from .pipeline import SyntheticRadioHost
        from .config import get_config
        
        # Initialize
        config = get_config()
        
        if not config.gemini_api_key:
            console.print(
                "[red]Error:[/red] GEMINI_API_KEY not found.\n"
                "Set it in your environment or .env file.",
                style="bold"
            )
            sys.exit(1)
        
        pipeline = SyntheticRadioHost(config)
        
        # Handle --from-script option (generate audio from existing script)
        if args.from_script:
            script_path = Path(args.from_script)
            if not script_path.exists():
                console.print(f"[red]Error:[/red] Script file not found: {script_path}")
                sys.exit(1)
            
            console.print(f"\n[bold]Loading script from:[/bold] {script_path}")
            
            with open(script_path, 'r', encoding='utf-8') as f:
                script_text = f.read()
            
            # Remove header lines (lines starting with #)
            lines = script_text.split('\n')
            script_lines = [l for l in lines if not l.startswith('#') and not l.startswith('=')]
            script_text = '\n'.join(script_lines).strip()
            
            output_path = args.output or script_path.with_suffix('.mp3')
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Generating audio from script...", total=None)
                final_path = pipeline.generate_from_script(
                    script_text=script_text,
                    output_path=str(output_path),
                    cleanup_temp=not args.no_cleanup
                )
                progress.remove_task(task)
            
            console.print(f"\n[bold green]✅ Audio Generated![/bold green]")
            console.print(f"[bold]Output file:[/bold] {final_path}")
            return
        
        console.print(f"\n[bold]Topic:[/bold] {args.topic}")
        console.print(f"[bold]Duration:[/bold] {args.duration} minutes")
        
        if args.script_only:
            # Generate script only
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Generating script...", total=None)
                script = pipeline.generate_script_only(args.topic, args.duration)
                progress.remove_task(task)
            
            console.print("\n[bold green]Generated Script:[/bold green]\n")
            console.print(Panel(script.raw_text, title="Script", border_style="green"))
            
        else:
            # Full generation
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Generating radio show...", total=None)
                result = pipeline.generate(
                    topic=args.topic,
                    duration_minutes=args.duration,
                    output_path=args.output,
                    cleanup_temp=not args.no_cleanup
                )
                progress.remove_task(task)
            
            # Print results
            console.print("\n[bold green]✅ Generation Complete![/bold green]\n")
            console.print(f"[bold]Output file:[/bold] {result.output_path}")
            console.print(f"[bold]Duration:[/bold] {result.duration_seconds:.1f} seconds")
            console.print(f"[bold]Dialogue turns:[/bold] {len(result.dialogues)}")
            
            # Show script preview
            preview = result.script.raw_text[:500] + "..." if len(result.script.raw_text) > 500 else result.script.raw_text
            console.print("\n[bold]Script Preview:[/bold]")
            console.print(Panel(preview, border_style="dim"))
            
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}", style="bold")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", style="bold")
        if args.verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()


