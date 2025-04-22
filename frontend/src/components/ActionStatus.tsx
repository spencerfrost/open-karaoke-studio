import React from 'react';
import { useApiQuery } from '../hooks/useApi';
import {
    Table,
    TableBody,
    TableCell,
    TableCaption,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";

interface Song {
    id: string;
    title: string;
    artist: string;
    // ... other song properties
}

const SongLibrary: React.FC = () => {
    const { data: songs, isLoading, isError, error } = useApiQuery<Song[], ['songs']>(
        ['songs'],
        '/songs'
    );

    if (isLoading) return <div>Loading song library...</div>;
    if (isError) return <div>Error: {error?.message}</div>;

    return (
        <div>
            <h2 className="text-xl font-semibold mb-4">Processed Songs Library:</h2>
            <Table>
                <TableCaption>A list of your available songs.</TableCaption>
                <TableHeader>
                    <TableRow>
                        <TableHead className="w-[100px]">Title</TableHead>
                        <TableHead>Artist</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {songs?.map((song) => (
                        <TableRow key={song.id}>
                            <TableCell className="font-medium">{song.title}</TableCell>
                            <TableCell>{song.artist}</TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
};

export default SongLibrary;